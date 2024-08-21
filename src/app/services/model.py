import math
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.core.exceptions import (
    ModelRetrievalError,
    BaseModelNotFoundError,
    FineTunedModelNotFoundError
)
from app.models.fine_tuning_job import FineTuningJob
from app.models.base_model import BaseModel
from app.models.fine_tuned_model import FineTunedModel
from app.schemas.common import Pagination
from app.schemas.model import BaseModelResponse, FineTunedModelResponse
from app.utils import setup_logger

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

    Raises:
        ModelRetrievalError: If there's an error retrieving the base models from the database.
    """
    try:
        logger.info(f"Fetching base models, page: {page}, items_per_page: {items_per_page}")

        # Count total items
        total_count = await db.scalar(select(func.count()).select_from(BaseModel))

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
            next_page=page + 1 if page < total_pages else None,
            previous_page=page - 1 if page > 1 else None
        )

        logger.info(f"Successfully retrieved {len(models)} base models")
        return models, pagination
    except Exception as e:
        logger.error(f"Error retrieving base models: {e}")
        raise ModelRetrievalError("Failed to retrieve base models from the database")


async def get_base_model(db: AsyncSession, model_name: str) -> BaseModelResponse | None:
    """
    Get a specific base model.

    Args:
        db (AsyncSession): The database session.
        model_name (str): The name of the base model to retrieve.

    Returns:
        BaseModelResponse | None: The base model if found, None otherwise.

    Raises:
        BaseModelNotFoundError: If the specified base model is not found in the database.
    """
    try:
        logger.info(f"Fetching base model: {model_name}")
        result = await db.execute(
            select(BaseModel)
            .where(BaseModel.name == model_name)
        )
        model = result.scalar_one_or_none()
        if model:
            logger.info(f"Successfully retrieved base model: {model_name}")
            return BaseModelResponse.from_orm(model)
        logger.warning(f"Base model not found: {model_name}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving base model {model_name}: {e}")
        raise BaseModelNotFoundError(f"Failed to retrieve base model '{model_name}' from the database")


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

    Raises:
        ModelRetrievalError: If there's an error retrieving the fine-tuned models from the database.
    """
    try:
        logger.info(f"Fetching fine-tuned models for user: {user_id}, page: {page}, items_per_page: {items_per_page}")

        # Count total items
        total_count = await db.scalar(
            select(func.count()).select_from(FineTunedModel).where(FineTunedModel.user_id == user_id)
        )

        # Calculate pagination
        total_pages = math.ceil(total_count / items_per_page)
        offset = (page - 1) * items_per_page

        # Join FineTunedModel with FineTuningJob to get the job name
        result = await db.execute(
            select(FineTunedModel, FineTuningJob.name.label('job_name'))
            .join(FineTuningJob, FineTunedModel.fine_tuning_job_id == FineTuningJob.id)
            .where(FineTunedModel.user_id == user_id)
            .offset(offset)
            .limit(items_per_page)
        )

        # Create FineTunedModelResponse objects with the job name included
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
            next_page=page + 1 if page < total_pages else None,
            previous_page=page - 1 if page > 1 else None
        )

        logger.info(f"Successfully retrieved {len(models)} fine-tuned models for user: {user_id}")
        return models, pagination
    except Exception as e:
        logger.error(f"Error retrieving fine-tuned models for user {user_id}: {e}")
        raise ModelRetrievalError("Failed to retrieve fine-tuned models from the database")


async def get_fine_tuned_model(db: AsyncSession, user_id: UUID, model_name: str) -> FineTunedModelResponse | None:
    """
    Get a specific fine-tuned model.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        model_name (str): The name of the fine-tuned model to retrieve.

    Returns:
        FineTunedModelResponse | None: The fine-tuned model if found, None otherwise.

    Raises:
        FineTunedModelNotFoundError: If the specified fine-tuned model is not found in the database.
    """
    try:
        logger.info(f"Fetching fine-tuned model: {model_name} for user: {user_id}")
        result = await db.execute(
            select(FineTunedModel, FineTuningJob.name.label('job_name'))
            .join(FineTuningJob, FineTunedModel.fine_tuning_job_id == FineTuningJob.id)
            .where(FineTunedModel.user_id == user_id, FineTunedModel.name == model_name)
        )
        row = result.first()
        if row:
            model, job_name = row
            model_dict = model.__dict__
            model_dict['fine_tuning_job_name'] = job_name
            logger.info(f"Successfully retrieved fine-tuned model: {model_name} for user: {user_id}")
            return FineTunedModelResponse(**model_dict)
        logger.warning(f"Fine-tuned model not found: {model_name} for user: {user_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving fine-tuned model {model_name} for user {user_id}: {e}")
        raise FineTunedModelNotFoundError(f"Failed to retrieve fine-tuned model '{model_name}' from the database")