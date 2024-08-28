from typing import Dict, Union, List

from fastapi import APIRouter, Depends
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.authentication import get_current_active_user
from app.core.database import get_db
from app.schemas.common import Pagination
from app.schemas.model import BaseModelResponse, FineTunedModelResponse
from app.schemas.user import UserResponse
from app.services.model import (
    get_base_models,
    get_base_model,
    get_fine_tuned_models,
    get_fine_tuned_model,
)
from app.core.utils import setup_logger

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
    """
    models, pagination = await get_base_models(db, page, items_per_page)
    logger.info(f"Retrieved {len(models)} base models, page: {page}")
    return {
        "data": models,
        "pagination": pagination
    }


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
    """
    model = await get_base_model(db, model_name)
    logger.info(f"Retrieved details for base model: {model_name}")
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
    """
    models, pagination = await get_fine_tuned_models(db, current_user.id, page, items_per_page)
    logger.info(f"Retrieved {len(models)} fine-tuned models for user: {current_user.id}")
    return {
        "data": models,
        "pagination": pagination
    }


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
    """
    model = await get_fine_tuned_model(db, current_user.id, model_name)
    logger.info(f"Retrieved details for fine-tuned model: {model_name}, user: {current_user.id}")
    return model