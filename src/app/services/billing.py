from datetime import date
from decimal import Decimal
from uuid import UUID

import stripe
from sqlalchemy import select, insert, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.common import paginate_query
from app.core.config_manager import config
from app.core.exceptions import ServerError, BadRequestError
from app.core.utils import setup_logger
from app.models.billing_credit import BillingCredit
from app.models.usage import Usage
from app.models.user import User
from app.schemas.billing import CreditCommitRequest, CreditHistoryResponse
from app.core.constants import UsageUnit, ServiceName
from app.schemas.common import Pagination

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)

# Initialize Stripe
stripe.api_key = config.stripe_secret_key


async def create_stripe_checkout_session(user_id: UUID):
    """
    Create a Stripe Checkout Session for adding credits.
    """
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Credits',
                    },
                    'unit_amount': 1000,  # $10.00
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{config.api_base_url}/billing/success',
            cancel_url=f'{config.api_base_url}/billing/cancel',
            client_reference_id=str(user_id),
        )
        return checkout_session
    except Exception as e:
        raise ServerError(f"Error creating Stripe checkout session: {str(e)}", logger)


async def commit_credits(request: CreditCommitRequest, db: AsyncSession) -> bool:
    """
    Check if a user has enough credits for a job, commit them if so, and log the usage.
    """
    # Get the user from the database
    user = (await db.execute(select(User).where(User.id == request.user_id))).scalar_one_or_none()
    # If user not found, log error and return
    if not user:
        raise BadRequestError(f"User not found: {request.user_id}")

    try:
        # Calculate the required credits based on usage amount, unit, and service
        required_credits = calculate_required_credits(request.usage_amount, request.usage_unit, request.service_name)

        if user.credits_balance >= required_credits:
            # Subtract credits from user's balance (this will commit to the users table)
            user.credits_balance -= required_credits
            # Log the credit deduction in billing_credits table
            await db.execute(
                insert(BillingCredit).values(
                    user_id=user.id,
                    credits=-required_credits
                )
            )
            # Log the usage in the usage table
            await db.execute(
                insert(Usage).values(
                    user_id=user.id,
                    usage_amount=request.usage_amount,
                    usage_unit=request.usage_unit,
                    cost=required_credits,
                    service_name=request.service_name,
                    fine_tuning_job_id=request.fine_tuning_job_id
                )
            )
            await db.commit()
            logger.info(f"Committed {required_credits} credits for user {request.user_id}")
            return True
        else:
            logger.info(f"Insufficient credits for user {request.user_id}. Required: {required_credits}, "
                        f"Available: {user.credits_balance}")
            return False
    except Exception as e:
        await db.rollback()
        raise ServerError(f"Error committing credits for user {request.user_id}: {str(e)}", logger)


def calculate_required_credits(usage_amount: int, usage_unit: str, service_name: str) -> Decimal:
    """
    Calculate the required credits based on usage amount, unit, and service.
    This is a placeholder function and should be replaced with actual pricing logic.
    """
    if service_name == ServiceName.FINE_TUNING and usage_unit == UsageUnit.TOKEN:
        # 3 credits per 1mil tokens
        return Decimal(3 * usage_amount / 1000000)

    # Return 422 if pricing logic not implemented for the requested service and unit
    raise BadRequestError(f"Pricing logic not implemented for service: {service_name} and unit: {usage_unit}")


async def add_credits_to_user(db: AsyncSession, user_id: UUID, amount: Decimal):
    """
    Add credits to a user's account and log the addition in the billing_credits table.
    """
    try:
        # Get the user from the database
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        # If user not found, log error and return
        if not user:
            logger.error(f"User not found: {user_id}")
            return

        # Add credits to user's balance (this will commit to the users table)
        user.credits_balance += amount
        # Log the credit addition in billing_credits table
        await db.execute(
            insert(BillingCredit).values(
                user_id=user.id,
                credits=amount
            )
        )
        await db.commit()
        logger.info(f"Added {amount} credits to user {user_id}")
    except Exception as e:
        await db.rollback()
        raise ServerError(f"Error adding credits to user {user_id}: {str(e)}", logger)


async def get_credit_history(
                db: AsyncSession,
                user_id: UUID,
                start_date: date | None = None,
                end_date: date | None = None,
                page: int = 1,
                items_per_page: int = 20
        ) -> tuple[list[CreditHistoryResponse], Pagination]:
    """
    Get the credit history for a user.
    """
    # Validate dates
    if start_date and end_date and end_date < start_date:
        raise BadRequestError(f"End date must be after start date; start_date: {start_date}, end_date: {end_date}")

    # Construct query
    query = select(BillingCredit).where(BillingCredit.user_id == user_id).order_by(BillingCredit.created_at.desc())
    if start_date:
        query = query.where(func.date(BillingCredit.created_at) >= start_date)
    if end_date:
        query = query.where(func.date(BillingCredit.created_at) <= end_date)

    # Execute query and paginate results
    results, pagination = await paginate_query(db, query, page, items_per_page)
    credit_history = [CreditHistoryResponse.from_orm(record) for record in results]
    return credit_history, pagination
