from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BillingTransactionType
from app.models.base_model import BaseModel
from app.models.billing_credit import BillingCredit
from app.models.fine_tuning_job import FineTuningJob


async def get_credit_record(
        db: AsyncSession,
        user_id: UUID,
        transaction_id: str,
        transaction_type: BillingTransactionType
) -> Optional[BillingCredit]:
    """
    Get a credit record by transaction details.

    Args:
        db: Database session
        user_id: User ID
        transaction_id: Transaction identifier
        transaction_type: Type of transaction

    Returns:
        Credit record if found, None otherwise
    """
    result = await db.execute(
        select(BillingCredit)
        .where(
            and_(
                BillingCredit.user_id == user_id,
                BillingCredit.transaction_id == transaction_id,
                BillingCredit.transaction_type == transaction_type
            )
        )
    )
    return result.scalar_one_or_none()


async def get_job_for_credits(
        db: AsyncSession,
        job_id: UUID,
        user_id: UUID
) -> Optional[Tuple[FineTuningJob, str]]:
    """Get a fine-tuning job and its base model name for credit calculation."""
    result = await db.execute(
        select(FineTuningJob, BaseModel.name.label('base_model_name'))
        .join(BaseModel, FineTuningJob.base_model_id == BaseModel.id)
        .where(
            FineTuningJob.id == job_id,
            FineTuningJob.user_id == user_id
        )
    )
    return result.first()


async def count_credit_history(
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date
) -> int:
    """
    Count total number of credit history records for a user within a date range.

    Args:
        db: Database session
        user_id: User ID
        start_date: Start date
        end_date: End date

    Returns:
        Total count of credit history records
    """
    query = select(func.count()).select_from(BillingCredit).where(
        and_(
            BillingCredit.user_id == user_id,
            func.date(BillingCredit.created_at) >= start_date,
            func.date(BillingCredit.created_at) <= end_date
        )
    )

    result = await db.execute(query)
    return result.scalar_one()


async def get_credit_history(
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date,
        offset: int,
        limit: int
) -> List[BillingCredit]:
    """
    Get credit history records for a user within a date range with pagination.

    Args:
        db: Database session
        user_id: User ID
        start_date: Start date
        end_date: End date
        offset: Pagination offset
        limit: Number of records to return

    Returns:
        List of credit history records
    """
    query = (
        select(BillingCredit)
        .where(
            and_(
                BillingCredit.user_id == user_id,
                func.date(BillingCredit.created_at) >= start_date,
                func.date(BillingCredit.created_at) <= end_date
            )
        )
        .order_by(BillingCredit.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    return result.scalars().all()
