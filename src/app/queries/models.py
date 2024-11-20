from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FineTunedModelStatus
from app.models.base_model import BaseModel
from app.models.fine_tuned_model import FineTunedModel
from app.models.fine_tuning_job import FineTuningJob
from app.queries.common import make_naive


async def get_base_model_by_name(db: AsyncSession, name: str) -> Optional[BaseModel]:
    """Get a base model by name."""
    result = await db.execute(
        select(BaseModel).where(BaseModel.name == name)
    )
    return result.scalar_one_or_none()

async def list_base_models(
        db: AsyncSession,
        offset: int,
        limit: int,
        exclude_dummy: bool = True
) -> List[BaseModel]:
    """List base models with pagination."""
    query = select(BaseModel).order_by(BaseModel.name.desc())
    if exclude_dummy:
        query = query.where(BaseModel.name != 'llm_dummy')
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def count_base_models(
        db: AsyncSession,
        exclude_dummy: bool = True
) -> int:
    """Count total number of base models."""
    query = select(func.count()).select_from(BaseModel)
    if exclude_dummy:
        query = query.where(BaseModel.name != 'llm_dummy')
    result = await db.execute(query)
    return result.scalar_one()

async def get_fine_tuned_model_by_name(
        db: AsyncSession,
        user_id: UUID,
        name: str
) -> Optional[Tuple[FineTunedModel, str]]:
    """Get a fine-tuned model by name with its associated job name."""
    result = await db.execute(
        select(FineTunedModel, FineTuningJob.name.label('job_name'))
        .join(FineTuningJob, FineTunedModel.fine_tuning_job_id == FineTuningJob.id)
        .where(
            and_(
                FineTunedModel.user_id == user_id,
                FineTunedModel.name == name,
                FineTunedModel.status != FineTunedModelStatus.DELETED
            )
        )
    )
    return result.first()

async def list_fine_tuned_models(
        db: AsyncSession,
        user_id: UUID,
        offset: int,
        limit: int
) -> List[Tuple[FineTunedModel, str]]:
    """List fine-tuned models with associated job names."""
    result = await db.execute(
        select(FineTunedModel, FineTuningJob.name.label('job_name'))
        .join(FineTuningJob, FineTunedModel.fine_tuning_job_id == FineTuningJob.id)
        .where(
            and_(
                FineTunedModel.user_id == user_id,
                FineTunedModel.status != FineTunedModelStatus.DELETED
            )
        )
        .order_by(FineTunedModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.all()

async def count_fine_tuned_models(
        db: AsyncSession,
        user_id: UUID
) -> int:
    """Count total number of fine-tuned models for a user."""
    result = await db.execute(
        select(func.count())
        .select_from(FineTunedModel)
        .where(
            and_(
                FineTunedModel.user_id == user_id,
                FineTunedModel.status != FineTunedModelStatus.DELETED
            )
        )
    )
    return result.scalar_one()

async def get_deleted_models(
        db: AsyncSession,
        cutoff_date: datetime
) -> List[FineTunedModel]:
    """
    Get recently deleted models that need weight cleanup.

    Args:
        db: Database session
        cutoff_date: Only include models deleted after this date

    Returns:
        List of deleted models with artifacts to clean up
    """
    query = (
        select(FineTunedModel)
        .where(
            and_(
                FineTunedModel.status == FineTunedModelStatus.DELETED,
                FineTunedModel.updated_at >= make_naive(cutoff_date),
                # Only include models that still have weight files
                FineTunedModel.artifacts.is_not(None)
            )
        )
        .order_by(FineTunedModel.updated_at.desc())
    )

    result = await db.execute(query)
    models = result.scalars().all()

    return models
