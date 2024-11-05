from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.common import paginate_query
from app.core.config_manager import config
from app.core.constants import FineTunedModelStatus
from app.core.exceptions import FineTunedModelNotFoundError
from app.core.utils import setup_logger
from app.models.fine_tuned_model import FineTunedModel
from app.models.fine_tuning_job import FineTuningJob
from app.schemas.common import Pagination
from app.schemas.model import FineTunedModelResponse
from app.services.model import logger

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
        logger.warning(f"FineTunedModel: {model.id} already exists")
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


async def get_fine_tuned_models(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[FineTunedModelResponse], Pagination]:
    """
    Get all fine-tuned models for a user with pagination.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        tuple[list[FineTunedModelResponse], Pagination]: A tuple containing the list of fine-tuned models and pagination info.
    """
    # Construct the query
    query = (
        select(FineTunedModel, FineTuningJob.name.label('job_name'))
        .join(FineTuningJob, FineTunedModel.fine_tuning_job_id == FineTuningJob.id)
        .where(
            FineTunedModel.user_id == user_id,
            FineTuningJob.status != FineTunedModelStatus.DELETED
        ).order_by(FineTunedModel.created_at.desc())
    )
    # Paginate the query
    results, pagination = await paginate_query(db, query, page, items_per_page)
    # Create response objects
    models = []
    for row in results:
        model_dict = row.FineTunedModel.__dict__
        model_dict['fine_tuning_job_name'] = row.job_name
        models.append(FineTunedModelResponse(**model_dict))
    # Log and return objects
    logger.info(f"Retrieved {len(models)} fine-tuned models for user: {user_id}, page: {page}")
    return models, pagination


async def get_fine_tuned_model(db: AsyncSession, user_id: UUID, model_name: str) -> FineTunedModelResponse:
    """
    Get a specific fine-tuned model.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        model_name (str): The name of the fine-tuned model.

    Returns:
        FineTunedModelResponse: The fine-tuned model if found.

    Raises:
        FineTunedModelNotFoundError: If the specified fine-tuned model is not found.
    """
    # Get the fine-tuned model from the database
    result = await db.execute(
        select(FineTunedModel, FineTuningJob.name.label('job_name'))
        .join(FineTuningJob, FineTunedModel.fine_tuning_job_id == FineTuningJob.id)
        .where(FineTunedModel.user_id == user_id, FineTunedModel.name == model_name)
    )
    row = result.first()

    # Raise an error if the fine-tuned model is not found
    if not row:
        raise FineTunedModelNotFoundError(f"Fine-tuned model not found: {model_name} for user: {user_id}", logger)

    # Prepare the response
    model, job_name = row
    model_dict = model.__dict__
    model_dict['fine_tuning_job_name'] = job_name

    # Log and return the fine-tuned model
    logger.info(f"Retrieved fine-tuned model: {model_name} for user: {user_id}")
    return FineTunedModelResponse(**model_dict)
