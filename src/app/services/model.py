from uuid import UUID
import math
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.models.fine_tuning_job import FineTuningJob
from app.models.base_model import BaseModel
from app.models.fine_tuned_model import FineTunedModel
from app.schemas.common import Pagination
from app.schemas.model import BaseModelResponse, FineTunedModelResponse
from app.utils import setup_logger
from app.core.exceptions import (
    BaseModelNotFoundError,
    FineTunedModelNotFoundError
)

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def get_base_models(
        db: AsyncSession,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[BaseModelResponse], Pagination]:
    """
    Get all available base LLM models with pagination.

    Args:
        db (AsyncSession): The database session.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        tuple[list[BaseModelResponse], Pagination]: A tuple containing the list of base models and pagination info.
    """
    # Count the total items
    total_count = await db.scalar(
        select(func.count()).select_from(BaseModel)
    )

    # Calculate pagination
    total_pages = math.ceil(total_count / items_per_page)
    offset = (page - 1) * items_per_page

    # Fetch items
    result = await db.execute(
        select(BaseModel)
        .offset(offset)
        .limit(items_per_page)
    )
    models = [BaseModelResponse.from_orm(model) for model in result.scalars().all()]

    # Create pagination object
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
    )

    # Log and return models and pagination
    logger.info(f"Retrieved {len(models)} base models, page: {page}")
    return models, pagination


async def get_base_model(db: AsyncSession, model_name: str) -> BaseModelResponse:
    """
    Get a specific base model.

    Args:
        db (AsyncSession): The database session.
        model_name (str): The name of the base model.

    Returns:
        BaseModelResponse: The base model if found.

    Raises:
        BaseModelNotFoundError: If the specified base model is not found.
    """
    # Get the base model from the database
    model = (await db.execute(
        select(BaseModel)
        .where(BaseModel.name == model_name)
    )).scalar_one_or_none()

    # Raise an error if the base model is not found
    if not model:
        raise BaseModelNotFoundError(f"Base model not found: {model_name}", logger)

    # Log and return the base model
    logger.info(f"Retrieved base model: {model_name}")
    return BaseModelResponse.from_orm(model)


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
    # Count the total items
    total_count = await db.scalar(
        select(func.count()).select_from(FineTunedModel).where(FineTunedModel.user_id == user_id)
    )

    # Calculate pagination
    total_pages = math.ceil(total_count / items_per_page)
    offset = (page - 1) * items_per_page

    # Fetch items
    result = await db.execute(
        select(FineTunedModel, FineTuningJob.name.label('job_name'))
        .join(FineTuningJob, FineTunedModel.fine_tuning_job_id == FineTuningJob.id)
        .where(FineTunedModel.user_id == user_id)
        .offset(offset)
        .limit(items_per_page)
    )

    models = []
    for row in result:
        model_dict = row.FineTunedModel.__dict__
        model_dict['fine_tuning_job_name'] = row.job_name
        models.append(FineTunedModelResponse(**model_dict))

    # Create pagination object
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
    )

    # Log and return models and pagination
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
