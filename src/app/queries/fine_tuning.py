from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import FineTuningJobStatus
from app.models.base_model import BaseModel
from app.models.dataset import Dataset
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.queries.common import make_naive, now_utc


async def get_job_with_details(
        db: AsyncSession,
        user_id: UUID,
        job_name: str
) -> Optional[Tuple[FineTuningJob, FineTuningJobDetail, str, str]]:
    """Get a fine-tuning job with its details and related names."""
    result = await db.execute(
        select(FineTuningJob, FineTuningJobDetail, BaseModel.name.label('base_model_name'),
               Dataset.name.label('dataset_name'))
        .join(FineTuningJobDetail)
        .join(BaseModel, FineTuningJob.base_model_id == BaseModel.id)
        .join(Dataset, FineTuningJob.dataset_id == Dataset.id)
        .where(
            FineTuningJob.user_id == user_id,
            FineTuningJob.name == job_name
        )
    )
    return result.first()


async def get_job_with_details_full(
        db: AsyncSession,
        job_id: UUID,
        user_id: UUID
) -> Optional[Tuple[FineTuningJob, Dataset, BaseModel, FineTuningJobDetail]]:
    """Get complete job details with all related entities."""
    result = await db.execute(
        select(FineTuningJob, Dataset, BaseModel, FineTuningJobDetail)
        .join(Dataset, FineTuningJob.dataset_id == Dataset.id)
        .join(BaseModel, FineTuningJob.base_model_id == BaseModel.id)
        .join(FineTuningJobDetail)
        .where(
            FineTuningJob.user_id == user_id,
            FineTuningJob.id == job_id
        )
    )
    return result.first()


async def get_job_by_id(
        db: AsyncSession,
        job_id: UUID,
        user_id: UUID
) -> Optional[FineTuningJob]:
    """Get a fine-tuning job by ID."""
    result = await db.execute(
        select(FineTuningJob)
        .options(selectinload(FineTuningJob.details))
        .where(
            FineTuningJob.id == job_id,
            FineTuningJob.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def list_jobs(
        db: AsyncSession,
        user_id: UUID,
        offset: int,
        limit: int,
        exclude_deleted: bool = True
) -> List[Tuple[FineTuningJob, str, str]]:
    """List fine-tuning jobs with related names."""
    query = (
        select(FineTuningJob, BaseModel.name.label('base_model_name'), Dataset.name.label('dataset_name'))
        .join(BaseModel, FineTuningJob.base_model_id == BaseModel.id)
        .join(Dataset, FineTuningJob.dataset_id == Dataset.id)
        .where(FineTuningJob.user_id == user_id)
    )
    if exclude_deleted:
        query = query.where(FineTuningJob.status != FineTuningJobStatus.DELETED)
    query = query.order_by(FineTuningJob.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    return result.all()


async def count_jobs(
        db: AsyncSession,
        user_id: UUID,
        exclude_deleted: bool = True
) -> int:
    """Count total number of fine-tuning jobs."""
    query = select(func.count()).select_from(FineTuningJob).where(FineTuningJob.user_id == user_id)
    if exclude_deleted:
        query = query.where(FineTuningJob.status != FineTuningJobStatus.DELETED)
    result = await db.execute(query)
    return result.scalar_one()


async def get_non_terminal_jobs(
        db: AsyncSession,
        statuses: List[FineTuningJobStatus],
        completed_within_minutes: Optional[int] = None
) -> List[FineTuningJob]:
    """Get all non-terminal jobs and recently completed jobs."""
    conditions = [FineTuningJob.status.in_(statuses)]

    if completed_within_minutes:
        recent_time = now_utc() - timedelta(minutes=completed_within_minutes)
        conditions.append(and_(
            FineTuningJob.status == FineTuningJobStatus.COMPLETED,
            FineTuningJob.updated_at >= make_naive(recent_time)
        ))

    result = await db.execute(
        select(FineTuningJob)
        .options(selectinload(FineTuningJob.details))
        .where(or_(*conditions))
    )
    return result.scalars().all()


async def get_jobs_for_status_update(
        db: AsyncSession,
        non_terminal_statuses: List[FineTuningJobStatus],
        recent_completed_cutoff: datetime
) -> List[FineTuningJob]:
    """
    Get jobs that need status updates.

    Args:
        db: Database session
        non_terminal_statuses: List of statuses to include
        recent_completed_cutoff: Cutoff time for recently completed jobs

    Returns:
        List of jobs with their details loaded

    Note:
        This includes both non-terminal jobs and recently completed jobs
    """
    query = (
        select(FineTuningJob)
        .options(
            selectinload(FineTuningJob.details),
            selectinload(FineTuningJob.fine_tuned_model)
        )
        .where(
            or_(
                # Get all non-terminal jobs
                FineTuningJob.status.in_(non_terminal_statuses),
                # Get recently completed jobs
                and_(
                    FineTuningJob.status == FineTuningJobStatus.COMPLETED,
                    FineTuningJob.updated_at >= make_naive(recent_completed_cutoff)
                )
            )
        )
        .order_by(FineTuningJob.updated_at.desc())
    )

    result = await db.execute(query)
    jobs = result.scalars().all()

    return jobs
