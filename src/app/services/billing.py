import asyncio
from datetime import datetime
from uuid import UUID

import stripe
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config_manager import config
from app.core.constants import BillingTransactionType, UsageUnit
from app.core.exceptions import (
    BadRequestError,
    PaymentNeededError,
    ServerError,
    UserNotFoundError
)
from app.core.stripe_client import (
    create_stripe_checkout_session,
    stripe_charge_offline, create_stripe_billing_portal_session
)
from app.core.utils import setup_logger
from app.models.billing_credit import BillingCredit
from app.models.fine_tuning_job import FineTuningJob
from app.models.usage import Usage
from app.models.user import User
from app.queries import billing as billing_queries
from app.queries import users as user_queries
from app.schemas.billing import (
    CreditDeductRequest,
    CreditAddRequest,
    CreditHistoryResponse
)
from app.schemas.common import Pagination

logger = setup_logger(__name__)


async def add_stripe_credits(
        user: User,
        amount_dollars: int,
        base_url: str
) -> str:
    """Create Stripe checkout session for adding credits."""
    success_url = (
        f"{config.ui_url}{config.ui_url_settings}?stripe_success=1"
        if not config.use_api_ui else base_url
    )
    cancel_url = (
        f"{config.ui_url}{config.ui_url_settings}?stripe_error=user_cancelled"
        if not config.use_api_ui else base_url
    )

    try:
        checkout_session = create_stripe_checkout_session(
            user, amount_dollars, success_url, cancel_url
        )
        return checkout_session.url
    except Exception as e:
        raise ServerError(f"Failed to create Stripe checkout session: {str(e)}", logger)


async def get_stripe_billing_portal_url(user: User, base_url: str) -> str:
    """ Create a Stripe billing portal session """
    billing_portal_session = create_stripe_billing_portal_session(
        user,
        config.ui_url + config.ui_url_settings + "?stripe_success=2" if not config.use_api_ui else base_url,
    )
    return billing_portal_session.url


async def add_manual_credits(
        db: AsyncSession,
        request: CreditAddRequest
) -> CreditHistoryResponse:
    """Add credits manually (admin only)."""
    # Verify user exists
    user = await user_queries.get_user_by_id(db, request.user_id)
    if not user:
        raise UserNotFoundError(f"User not found: {request.user_id}", logger)

    try:
        # Add credits to user's balance
        user.credits_balance += request.amount

        # Record credit addition
        credit_record = BillingCredit(
            user_id=user.id,
            credits=request.amount,
            transaction_id=request.transaction_id,
            transaction_type=BillingTransactionType.MANUAL_ADJUSTMENT
        )
        db.add(credit_record)
        await db.commit()
        await db.refresh(credit_record)

        logger.info(f"Added {request.amount} credits to user: {user.id}")
        return CreditHistoryResponse.from_orm(credit_record)
    except IntegrityError:
        await db.rollback()
        raise BadRequestError(f"Transaction already exists: {request.transaction_id}, "
                              f"use a different transaction ID", logger)
    except Exception as e:
        await db.rollback()
        raise ServerError(f"Failed to add credits: {str(e)}", logger)


async def deduct_credits(
        request: CreditDeductRequest,
        db: AsyncSession,
        retry: bool = False
) -> CreditHistoryResponse:
    """Deduct credits for a service usage."""
    # Get job and user information
    user = await user_queries.get_user_by_id(db, request.user_id)
    if not user:
        raise BadRequestError(f"User not found: {request.user_id}")

    job_info = await billing_queries.get_job_for_credits(db, request.fine_tuning_job_id, request.user_id)
    if not job_info:
        raise BadRequestError(f"Job not found: {request.fine_tuning_job_id}")

    job, base_model_name = job_info

    # Check for existing deduction
    existing_credit = await billing_queries.get_credit_record(
        db,
        request.user_id,
        str(job.id),
        BillingTransactionType.FINE_TUNING_JOB
    )
    if existing_credit:
        return CreditHistoryResponse.from_orm(existing_credit)

    # Calculate required credits
    required_credits = await calculate_required_credits(
        request.usage_amount,
        request.usage_unit,
        base_model_name
    )

    try:
        if user.credits_balance >= required_credits:
            return await process_credit_deduction(db, user, job, required_credits, request)
        elif retry:
            return await handle_insufficient_credits(
                db, user, job, required_credits, request
            )
        else:
            raise PaymentNeededError(f"Insufficient credits: {user.credits_balance}/{required_credits}", logger)

    except Exception as e:
        await db.rollback()
        raise e


async def process_credit_deduction(
        db: AsyncSession,
        user: User,
        job: FineTuningJob,
        required_credits: float,
        request: CreditDeductRequest
) -> CreditHistoryResponse:
    """Process credit deduction transaction."""
    # Deduct credits
    user.credits_balance -= required_credits
    job.num_tokens = request.usage_amount

    # Record deduction
    credit_record = BillingCredit(
        user_id=user.id,
        credits=-required_credits,
        transaction_id=str(job.id),
        transaction_type=BillingTransactionType.FINE_TUNING_JOB
    )
    db.add(credit_record)

    # Record usage
    usage_record = Usage(
        user_id=user.id,
        usage_amount=request.usage_amount,
        usage_unit=request.usage_unit,
        cost=required_credits,
        service_name=request.service_name,
        fine_tuning_job_id=job.id
    )
    db.add(usage_record)

    await db.commit()
    await db.refresh(credit_record)

    logger.info(f"Deducted {required_credits} credits for user: {user.id}, job: {job.id}")
    return CreditHistoryResponse.from_orm(credit_record)


async def handle_insufficient_credits(
        db: AsyncSession,
        user: User,
        job: FineTuningJob,
        required_credits: float,
        request: CreditDeductRequest
) -> CreditHistoryResponse:
    """Handle case where user has insufficient credits with retry."""
    credits_to_charge = required_credits - user.credits_balance

    # Attempt offline charge
    if not stripe_charge_offline(user, float(credits_to_charge)):
        raise PaymentNeededError(f"Failed to charge user: {user.id}", logger)

    logger.info(f"Recharged user: {user.id} with {credits_to_charge} credits")
    await asyncio.sleep(20)  # Allow time for payment processing
    await db.refresh(user)

    # Retry deduction
    return await deduct_credits(request, db, retry=False)


async def handle_stripe_webhook(request: Request, db: AsyncSession):
    """Handle Stripe webhook callbacks."""
    # Verify webhook signature
    payload = await request.body()
    sig_header = request.headers['stripe-signature']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, config.stripe_webhook_secret
        )
    except Exception as e:
        logger.error(f"Invalid Stripe webhook: {str(e)}")
        return {"status": "error"}

    try:
        if event["type"] == "charge.succeeded":
            await handle_successful_charge(db, event["data"]["object"])
        elif event["type"] == "customer.updated":
            await handle_customer_update(db, event["data"]["object"])
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return {"status": "error"}

    return {"status": "success"}


async def get_credit_history(
        db: AsyncSession,
        user_id: UUID,
        start_date_str: str,
        end_date_str: str,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[CreditHistoryResponse], Pagination]:
    """
    Get credit history for a user with date filtering and pagination.

    Args:
        db: Database session
        user_id: User ID
        start_date_str: Start date in YYYY-MM-DD format
        end_date_str: End date in YYYY-MM-DD format
        page: Page number
        items_per_page: Number of items per page

    Returns:
        Tuple of list of credit history records and pagination info

    Raises:
        BadRequestError: If dates are invalid or end date is before start date
    """
    # Parse and validate dates
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise BadRequestError(
            "Invalid date format. Please use YYYY-MM-DD format"
        )

    if end_date < start_date:
        raise BadRequestError(
            f"End date ({end_date}) must be after start date ({start_date})"
        )

    # Calculate pagination
    offset = (page - 1) * items_per_page

    # Get total count for pagination
    total_count = await billing_queries.count_credit_history(
        db,
        user_id,
        start_date,
        end_date
    )

    # Calculate total pages
    total_pages = (total_count + items_per_page - 1) // items_per_page

    # Create pagination object
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page
    )

    # Get credit history records
    credits = await billing_queries.get_credit_history(
        db,
        user_id,
        start_date,
        end_date,
        offset,
        items_per_page
    )

    # Convert to response objects
    credit_responses = [
        CreditHistoryResponse.from_orm(credit)
        for credit in credits
    ]

    logger.info(
        f"Retrieved {len(credit_responses)} credit history records for user: "
        f"{user_id} between {start_date} and {end_date}"
    )

    return credit_responses, pagination


async def handle_successful_charge(db: AsyncSession, charge_data: dict) -> None:
    """
    Handle a successful Stripe charge by adding credits to user's account.

    Args:
        db: Database session
        charge_data: Stripe charge event data

    Raises:
        ServerError: If user not found or credit addition fails
    """
    try:
        # Extract charge information
        stripe_customer_id = charge_data["customer"]
        amount_cents = charge_data["amount_captured"]
        transaction_id = charge_data["id"]

        # Convert cents to dollars and then to credits (1:1 ratio for dollars to credits)
        amount_dollars = amount_cents / 100

        # Find user by Stripe customer ID
        user = await user_queries.get_user_by_stripe_customer_id(db, stripe_customer_id)
        if not user:
            raise ServerError(
                f"User not found for Stripe customer: {stripe_customer_id}",
                logger
            )

        # Add credits to user's balance
        user.credits_balance += amount_dollars

        # Record the credit addition
        credit_record = BillingCredit(
            user_id=user.id,
            credits=amount_dollars,
            transaction_id=transaction_id,
            transaction_type=BillingTransactionType.STRIPE_CHECKOUT
        )
        db.add(credit_record)

        await db.commit()
        logger.info(
            f"Added {amount_dollars} credits to user {user.id} "
            f"from Stripe charge {transaction_id}"
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to process successful charge: {str(e)}")
        raise ServerError(f"Failed to process charge: {str(e)}", logger)


async def handle_customer_update(db: AsyncSession, customer_data: dict) -> None:
    """
    Handle Stripe customer update events, particularly payment method changes.

    Args:
        db: Database session
        customer_data: Stripe customer update event data

    Raises:
        ServerError: If user not found or update fails
    """
    try:
        # Extract customer information
        stripe_customer_id = customer_data["id"]
        default_payment_method = customer_data["invoice_settings"]["default_payment_method"]

        # Find user by Stripe customer ID
        user = await user_queries.get_user_by_stripe_customer_id(db, stripe_customer_id)
        if not user:
            raise ServerError(
                f"User not found for Stripe customer: {stripe_customer_id}",
                logger
            )

        # Update user's payment method
        user.stripe_payment_method_id = default_payment_method
        await db.commit()

        logger.info(
            f"Updated payment method for user {user.id} "
            f"to {default_payment_method}"
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to process customer update: {str(e)}")
        raise ServerError(f"Failed to process customer update: {str(e)}", logger)


async def calculate_required_credits(
        usage_amount: int,
        usage_unit: str,
        base_model_name: str
) -> float:
    """
    Calculate required credits based on usage amount and model type.

    Args:
        usage_amount: Amount of usage (e.g., number of tokens)
        usage_unit: Unit of usage (e.g., TOKEN)
        base_model_name: Name of the base model

    Returns:
        Required credits amount

    Raises:
        BadRequestError: If pricing logic not implemented for the model or unit
    """
    if usage_unit != UsageUnit.TOKEN:
        raise BadRequestError(
            f"Pricing not implemented for usage unit: {usage_unit}"
        )

    # Convert token count to millions for pricing
    tokens_in_millions = usage_amount / 1_000_000

    # Define pricing tiers based on model
    model_pricing = {
        'llm_llama3_1_8b': 2.0,  # $2 per million tokens
        'llm_llama3_1_70b': 10.0,  # $10 per million tokens
        'llm_dummy': 2.0,  # $2 per million tokens for testing
    }

    # Get price per million tokens for the model
    price_per_million = model_pricing.get(base_model_name)
    if price_per_million is None:
        raise BadRequestError(
            f"Pricing not implemented for base model: {base_model_name}"
        )

    # Calculate total credits needed (1 credit = $1)
    required_credits = tokens_in_millions * price_per_million

    logger.info(
        f"Calculated credits for {usage_amount} tokens "
        f"using {base_model_name}: {required_credits}"
    )

    return required_credits


async def add_credits_to_user(
        db: AsyncSession,
        user_id: UUID,
        amount: float,
        transaction_id: str,
        transaction_type: BillingTransactionType
) -> CreditHistoryResponse:
    """
    Add credits to a user's account and record the transaction.

    Args:
        db: Database session
        user_id: User ID
        amount: Amount of credits to add
        transaction_id: Unique transaction identifier
        transaction_type: Type of credit transaction

    Returns:
        Credit history record

    Raises:
        UserNotFoundError: If user not found
        BadRequestError: If transaction already exists
        ServerError: If credit addition fails
    """
    # Verify user exists
    user = await user_queries.get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(f"User not found: {user_id}", logger)

    # Check for existing transaction
    existing_credit = await billing_queries.get_credit_record(
        db,
        user_id,
        transaction_id,
        transaction_type
    )
    if existing_credit:
        raise BadRequestError(
            f"Transaction already exists: {transaction_id}",
            logger
        )

    try:
        # Add credits to user's balance
        user.credits_balance += amount

        # Record the credit addition
        credit_record = BillingCredit(
            user_id=user_id,
            credits=amount,
            transaction_id=transaction_id,
            transaction_type=transaction_type
        )
        db.add(credit_record)

        # Commit changes
        await db.commit()
        await db.refresh(credit_record)

        logger.info(
            f"Added {amount} credits to user {user_id} "
            f"(transaction: {transaction_id}, type: {transaction_type})"
        )

        return CreditHistoryResponse.from_orm(credit_record)

    except Exception as e:
        await db.rollback()
        raise ServerError(f"Failed to add credits: {str(e)}", logger)
