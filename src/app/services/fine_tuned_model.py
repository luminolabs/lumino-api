from typing import Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.exceptions import FineTunedModelNotFoundError
from app.core.utils import setup_logger
from app.queries import fine_tuned_models as ft_models_queries
from app.queries import fine_tuning as ft_jobs_queries
from app.schemas.common import Pagination
from app.schemas.model import FineTunedModelResponse

logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def get_fine_tuned_models(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[FineTunedModelResponse], Pagination]:
    """Get all fine-tuned models for a user with pagination."""
    offset = (page - 1) * items_per_page

    # Get total count and paginated results
    total_count = await ft_models_queries.count_models(db, user_id)
    results = await ft_models_queries.list_models(db, user_id, offset, items_per_page)

    # Calculate pagination
    total_pages = (total_count + items_per_page - 1) // items_per_page
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
    )

    # Create response objects
    models = []
    for model, job_name in results:
        model_dict = model.__dict__
        model_dict['fine_tuning_job_name'] = job_name
        models.append(FineTunedModelResponse(**model_dict))

    logger.info(f"Retrieved {len(models)} fine-tuned models for user: {user_id}, page: {page}")
    return models, pagination


async def get_fine_tuned_model(
        db: AsyncSession,
        user_id: UUID,
        model_name: str
) -> FineTunedModelResponse:
    """Get detailed information about a specific fine-tuned model."""
    result = await ft_models_queries.get_model_by_name(db, user_id, model_name)
    if not result:
        raise FineTunedModelNotFoundError(f"Fine-tuned model not found: {model_name} for user: {user_id}", logger)

    model, job_name = result
    model_dict = model.__dict__
    model_dict['fine_tuning_job_name'] = job_name

    logger.info(f"Retrieved fine-tuned model: {model_name} for user: {user_id}")
    return FineTunedModelResponse(**model_dict)


async def create_fine_tuned_model(
        db: AsyncSession,
        job_id: UUID,
        user_id: UUID,
        artifacts: Dict[str, Any]
) -> bool:
    """
    Create a fine-tuned model record from job artifacts.

    Args:
        db: Database session
        job_id: Fine-tuning job ID
        user_id: User ID
        artifacts: Model artifacts (weights, configs, etc.)

    Returns:
        True if model was created, False if skipped

    Note:
        This is idempotent - it won't create duplicate models
        for the same job
    """
    # Check if the job exists and belongs to the user
    job = await ft_jobs_queries.get_job_by_id(db, job_id, user_id)
    if not job:
        logger.warning(f"Cannot create model: Job {job_id} not found for user {user_id}")
        return False

    # Check if a model already exists for this job
    existing_model = await ft_models_queries.get_existing_model(db, job_id, user_id)
    if existing_model:
        logger.warning(f"Model already exists for job {job_id}: {existing_model.id}")
        return True

    try:
        # Create new model
        model = await ft_models_queries.create_model(
            db,
            job_id,
            user_id,
            f"{job.name}_model",
            artifacts
        )
        await db.commit()

        logger.info(f"Created fine-tuned model for job {job_id}: {model.id}")
        return True

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create model for job {job_id}: {str(e)}")
        return False
