from datetime import date
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fine_tuning_job import FineTuningJob
from app.models.usage import Usage


async def get_usage_records(
        db: AsyncSession,
        user_id: UUID,
        start_date: Optional[date],
        end_date: Optional[date],
        offset: int,
        limit: int
) -> List[Tuple[Usage, str]]:
    """
    Get usage records with associated job names.

    Args:
        db: Database session
        user_id: User ID
        start_date: Optional start date filter
        end_date: Optional end date filter
        offset: Pagination offset
        limit: Number of records to return

    Returns:
        List of tuples containing Usage record and job name
    """
    query = (
        select(Usage, FineTuningJob.name.label('job_name'))
        .join(FineTuningJob, Usage.fine_tuning_job_id == FineTuningJob.id)
        .where(Usage.user_id == user_id)
    )

    if start_date:
        query = query.where(func.date(Usage.created_at) >= start_date)
    if end_date:
        query = query.where(func.date(Usage.created_at) <= end_date)

    query = (
        query.order_by(Usage.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    return result.all()


async def count_usage_records(
        db: AsyncSession,
        user_id: UUID,
        start_date: Optional[date],
        end_date: Optional[date]
) -> int:
    """Count total usage records for pagination."""
    query = select(func.count()).select_from(Usage).where(Usage.user_id == user_id)

    if start_date:
        query = query.where(func.date(Usage.created_at) >= start_date)
    if end_date:
        query = query.where(func.date(Usage.created_at) <= end_date)

    result = await db.execute(query)
    return result.scalar_one()


async def get_total_cost(
        db: AsyncSession,
        user_id: UUID,
        start_date: Optional[date],
        end_date: Optional[date]
) -> float:
    """Calculate total cost for the specified period."""
    query = select(func.sum(Usage.cost)).where(Usage.user_id == user_id)

    if start_date:
        query = query.where(func.date(Usage.created_at) >= start_date)
    if end_date:
        query = query.where(func.date(Usage.created_at) <= end_date)

    result = await db.execute(query)
    total_cost = result.scalar_one_or_none()
    return float(total_cost) if total_cost else 0.0
