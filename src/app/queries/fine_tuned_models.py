from typing import Dict, Any, Optional, Tuple, List
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fine_tuned_model import FineTunedModel
from app.models.fine_tuning_job import FineTuningJob


async def get_existing_model(
        db: AsyncSession,
        job_id: UUID,
        user_id: UUID
) -> Optional[FineTunedModel]:
    """Get existing model for a job if it exists."""
    result = await db.execute(
        select(FineTunedModel)
        .where(
            FineTunedModel.user_id == user_id,
            FineTunedModel.fine_tuning_job_id == job_id,
        )
        .order_by(FineTunedModel.created_at.desc())
    )
    return result.scalar_one_or_none()

async def create_model(
        db: AsyncSession,
        job_id: UUID,
        user_id: UUID,
        name: str,
        artifacts: Dict[str, Any]
) -> FineTunedModel:
    """Create a new fine-tuned model."""
    model = FineTunedModel(
        user_id=user_id,
        fine_tuning_job_id=job_id,
        name=name,
        artifacts=artifacts
    )
    db.add(model)
    return model

async def get_model_by_name(
        db: AsyncSession,
        user_id: UUID,
        model_name: str
) -> Optional[Tuple[FineTunedModel, str]]:
    """Get a fine-tuned model by name with its job name."""
    result = await db.execute(
        select(FineTunedModel, FineTuningJob.name.label('job_name'))
        .join(FineTuningJob, FineTunedModel.fine_tuning_job_id == FineTuningJob.id)
        .where(
            and_(
                FineTunedModel.user_id == user_id,
                FineTunedModel.name == model_name
            )
        )
    )
    return result.first()

async def list_models(
        db: AsyncSession,
        user_id: UUID,
        offset: int,
        limit: int
) -> List[Tuple[FineTunedModel, str]]:
    """List fine-tuned models with job names."""
    result = await db.execute(
        select(FineTunedModel, FineTuningJob.name.label('job_name'))
        .join(FineTuningJob, FineTunedModel.fine_tuning_job_id == FineTuningJob.id)
        .where(FineTunedModel.user_id == user_id)
        .order_by(FineTunedModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.all()

async def count_models(db: AsyncSession, user_id: UUID) -> int:
    """Count total number of fine-tuned models for a user."""
    result = await db.execute(
        select(func.count())
        .select_from(FineTunedModel)
        .where(FineTunedModel.user_id == user_id)
    )
    return result.scalar_one()
