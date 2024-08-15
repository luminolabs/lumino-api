from typing import Dict, Union, List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.core.authentication import get_current_active_user
from app.core.exceptions import (
    BaseModelNotFoundError,
    FineTunedModelNotFoundError,
    ModelRetrievalError
)
from app.database import get_db
from app.schemas.common import Pagination
from app.schemas.model import BaseModelResponse, FineTunedModelResponse
from app.schemas.user import UserResponse
from app.services.model import (
    get_base_models,
    get_base_model,
    get_fine_tuned_models,
    get_fine_tuned_model,
)
from app.utils import setup_logger

# Set up router
router = APIRouter(tags=["Models"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.get("/models/base", response_model=Dict[str, Union[List[BaseModelResponse], Pagination]])
async def list_base_models(
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1, description="Page number"),
        items_per_page: int = Query(20, ge=1, le=100, description="Number of items per page")
) -> Dict[str, Union[List[BaseModelResponse], Pagination]]:
    """
    List all available base LLM models.

    Args:
        db (AsyncSession): The database session.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        Dict[str, Union[List[BaseModelResponse], Pagination]]: A dictionary containing the list of base models and pagination info.

    Raises:
        ModelRetrievalError: If there's an error retrieving the base models.
    """
    try:
        logger.info(f"Fetching base models, page: {page}, items_per_page: {items_per_page}")
        models, pagination = await get_base_models(db, page, items_per_page)
        logger.info(f"Successfully retrieved {len(models)} base models")
        return {
            "data": models,
            "pagination": pagination
        }
    except ModelRetrievalError as e:
        logger.error(f"Error retrieving base models: {str(e)}")
        raise


@router.get("/models/base/{model_name}", response_model=BaseModelResponse)
async def get_base_model_details(
        model_name: str,
        db: AsyncSession = Depends(get_db),
) -> BaseModelResponse:
    """
    Get detailed information about a specific base model.

    Args:
        model_name (str): The name of the base model.
        db (AsyncSession): The database session.

    Returns:
        BaseModelResponse: The detailed information about the base model.

    Raises:
        BaseModelNotFoundError: If the specified base model is not found.
    """
    logger.info(f"Fetching details for base model: {model_name}")
    model = await get_base_model(db, model_name)
    if not model:
        logger.warning(f"Base model not found: {model_name}")
        raise BaseModelNotFoundError(f"Base model '{model_name}' not found")
    logger.info(f"Successfully retrieved details for base model: {model_name}")
    return model


@router.get("/models/fine-tuned", response_model=Dict[str, Union[List[FineTunedModelResponse], Pagination]])
async def list_fine_tuned_models(
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1, description="Page number"),
        items_per_page: int = Query(20, ge=1, le=100, description="Number of items per page")
) -> Dict[str, Union[List[FineTunedModelResponse], Pagination]]:
    """
    List all fine-tuned models for the current user.

    Args:
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        Dict[str, Union[List[FineTunedModelResponse], Pagination]]: A dictionary containing the list of fine-tuned models and pagination info.

    Raises:
        ModelRetrievalError: If there's an error retrieving the fine-tuned models.
    """
    try:
        logger.info(f"Fetching fine-tuned models for user: {current_user.id}, page: {page}, items_per_page: {items_per_page}")
        models, pagination = await get_fine_tuned_models(db, current_user.id, page, items_per_page)
        logger.info(f"Successfully retrieved {len(models)} fine-tuned models for user: {current_user.id}")
        return {
            "data": models,
            "pagination": pagination
        }
    except ModelRetrievalError as e:
        logger.error(f"Error retrieving fine-tuned models for user {current_user.id}: {str(e)}")
        raise


@router.get("/models/fine-tuned/{model_name}", response_model=FineTunedModelResponse)
async def get_fine_tuned_model_details(
        model_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTunedModelResponse:
    """
    Get detailed information about a specific fine-tuned model.

    Args:
        model_name (str): The name of the fine-tuned model.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        FineTunedModelResponse: The detailed information about the fine-tuned model.

    Raises:
        FineTunedModelNotFoundError: If the specified fine-tuned model is not found.
    """
    logger.info(f"Fetching details for fine-tuned model: {model_name}, user: {current_user.id}")
    model = await get_fine_tuned_model(db, current_user.id, model_name)
    if not model:
        logger.warning(f"Fine-tuned model not found: {model_name} for user: {current_user.id}")
        raise FineTunedModelNotFoundError(f"Fine-tuned model '{model_name}' not found")
    logger.info(f"Successfully retrieved details for fine-tuned model: {model_name}, user: {current_user.id}")
    return model