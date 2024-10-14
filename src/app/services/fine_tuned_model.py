from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import FineTuningJobStatus
from app.core.utils import setup_logger
from app.models.fine_tuned_model import FineTunedModel
from app.models.fine_tuning_job import FineTuningJob

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def create_fine_tuned_model(db: AsyncSession,
                                  job_id: UUID, user_id: UUID, artifacts: dict) -> bool:
    """Update the fine_tuned_models table with the new artifacts."""
    
    # First, confirm that the FineTuningJob exists
    job_query = select(FineTuningJob).where(
        FineTuningJob.id == job_id, FineTuningJob.user_id == user_id)
    job_result = await db.execute(job_query)
    job = job_result.scalar_one_or_none()
    if not job:
        logger.warning(f"No FineTuningJob found for job_id: {job_id} and user_id: {user_id}")
        return False

    # Check if a FineTunedModel already exists for this job
    model_query = (
        select(FineTunedModel)
        .where(FineTunedModel.fine_tuning_job_id == job_id)
        .order_by(FineTunedModel.created_at.desc())
    )
    model_result = await db.execute(model_query)
    model = model_result.scalar_one_or_none()
    if model:
        # Model exists, do nothing
        logger.error(f"FineTunedModel: {model.id} already exists - "
                     f"this should not happen; check pipeline-zen logic")
        return True

    # Create new model
    model = FineTunedModel(
        user_id=user_id,
        fine_tuning_job_id=job_id,
        name=f"{job.name}_model",
        artifacts=artifacts
    )
    db.add(model)
    await db.commit()
    logger.info(f"Successfully created FineTunedModel: {model.id} "
                f"for job_id: {job_id} and user_id: {user_id}")
    return True
