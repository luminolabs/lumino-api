import asyncio
from datetime import date
from decimal import Decimal
from uuid import UUID

from asyncpg import UniqueViolationError
from sqlalchemy import select, insert, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.common import paginate_query
from app.core.config_manager import config
from app.core.constants import UsageUnit, ServiceName, BillingTransactionType
from app.core.exceptions import ServerError, BadRequestError
from app.core.stripe_client import stripe_charge_offline
from app.core.utils import setup_logger
from app.models.base_model import BaseModel
from app.models.billing_credit import BillingCredit
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.models.usage import Usage
from app.models.user import User
from app.schemas.billing import CreditDeductRequest, CreditHistoryResponse
from app.schemas.common import Pagination

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def add_credits_to_user(db: AsyncSession, user: User, amount_dollars: float,
                              transaction_id: str, transaction_type: BillingTransactionType) -> None:
    """
    Add credits to a user's account and log the addition in the billing_credits table.
    """
    try:
        # If user not found, log error and return
        if not user:
            logger.error(f"User not found: {user.id}")
            return

        # Add credits to user's balance (this will commit to the users table)
        user.credits_balance += Decimal(amount_dollars)
        # Log the credit addition in billing_credits table
        await db.execute(
            insert(BillingCredit).values(
                user_id=user.id,
                credits=Decimal(amount_dollars),
                transaction_id=transaction_id,
                transaction_type=transaction_type
            )
        )
        await db.commit()
        logger.info(f"Added {amount_dollars} credits to user {user.id}")
    except UniqueViolationError:
        # We already added credits for this transaction, log warning and return
        logger.warning(f"Transaction ID already exists: {transaction_id}")
        return
    except Exception as e:
        await db.rollback()
        raise ServerError(f"Error adding credits to user {user.id}: {str(e)}", logger)


async def deduct_credits_for_fine_tuning_job(request: CreditDeductRequest, db: AsyncSession,
                                             retry: bool = False) -> bool:
    """
    Check if a user has enough credits for a job, deduct them if so, and log the usage.
    TODO: Make this function more generic to handle other services and units in the future.
    """
    # Get the user from the database
    user = (await db.execute(select(User).where(User.id == request.user_id))).scalar_one_or_none()
    # If user not found, log error and return
    if not user:
        raise BadRequestError(f"User not found: {request.user_id}")
    # If job not found, log error and return
    job = (await db.execute(select(FineTuningJob).where(
        FineTuningJob.id == request.fine_tuning_job_id,
        FineTuningJob.user_id == request.user_id))).scalar_one_or_none()
    if not job:
        raise BadRequestError(f"Fine-tuning job not found: {request.fine_tuning_job_id}")

    # Check if the job is already deducted
    billing_credit = (await db.execute(select(BillingCredit).where(
        BillingCredit.user_id == request.user_id,
        BillingCredit.transaction_id == str(job.id),
        BillingCredit.transaction_type == BillingTransactionType.FINE_TUNING_JOB))).scalar_one_or_none()
    if billing_credit:
        logger.info(f"Fine-tuning job {request.fine_tuning_job_id} already deducted")
        # We already charged the user for this job, allow the request to proceed
        return True

    # Calculate the required credits based on usage amount, unit, and service
    required_credits = await calculate_required_credits(
        request.usage_amount, request.usage_unit,
        user.id, job.id, request.service_name,
        db)

    if user.credits_balance >= required_credits:
        try:
            # Subtract credits from user's balance (this will deduct to the users table)
            user.credits_balance -= required_credits
            # Add token count to job table
            job.num_tokens = request.usage_amount
            # Log the credit deduction in billing_credits table
            await db.execute(
                insert(BillingCredit).values(
                    user_id=user.id,
                    credits=-required_credits,
                    transaction_id=str(job.id),
                    transaction_type=BillingTransactionType.FINE_TUNING_JOB
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
                    fine_tuning_job_id=str(job.id)
                )
            )
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise ServerError(f"Error deducting credits for user {request.user_id}: {str(e)}", logger)
        logger.info(f"Deducted {required_credits} credits for user {request.user_id}")
        return True
    elif retry:
        # If user doesn't have enough credits, charge them offline
        credits_to_charge = required_credits - user.credits_balance
        stripe_charge_offline(user, float(credits_to_charge))

        logger.info(f"Insufficient credits for user {request.user_id}. "
                    f"Re-charged user: {required_credits} credits,"
                    f"Required: {required_credits}, "
                    f"Available: {user.credits_balance}")

        # Allow time to process the payment
        await asyncio.sleep(20)
        await db.refresh(user)  # Refresh the credits balance field
        # Retry the deduction
        return await deduct_credits_for_fine_tuning_job(request, db, retry=False)

    # If we reach this point, the user doesn't have enough credits, and we couldn't charge them
    return False


async def calculate_required_credits(
        usage_amount: int, usage_unit: str,
        user_id: UUID, service_id: UUID, service_name: str,
        db: AsyncSession) -> Decimal:
    """
    Calculate the required credits based on usage amount, unit, and service.
    This is a placeholder function and should be replaced with actual pricing logic.
    """
    if service_name == ServiceName.FINE_TUNING_JOB and usage_unit == UsageUnit.TOKEN:
        result = await db.execute(
            select(FineTuningJob, BaseModel.name.label('base_model_name'))
            .join(BaseModel, FineTuningJob.base_model_id == BaseModel.id)
            .where(FineTuningJob.user_id == user_id, FineTuningJob.id == service_id)
        )
        job, base_model_name = result.first()
        if base_model_name == 'llm_llama3_1_8b':
            return Decimal(2 * usage_amount / 1000000)
        elif base_model_name == 'llm_llama3_1_70b':
            return Decimal(10 * usage_amount / 1000000)
        # Return 422 if pricing logic not implemented for this base model
        raise BadRequestError(f"Could not find pricing logic for base model: {base_model_name}")

    # Return 422 if pricing logic not implemented for the requested service and unit
    raise BadRequestError(f"Pricing logic not implemented for service: {service_name} and unit: {usage_unit}")


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
