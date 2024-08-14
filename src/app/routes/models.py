from typing import Dict, Union, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import Pagination
from app.schemas.model import BaseModelResponse, FineTunedModelResponse
from app.services.model import (
    get_base_models,
    get_base_model,
    get_fine_tuned_models,
    get_fine_tuned_model,
)
from app.core.authentication import get_current_active_user
from app.schemas.user import UserResponse

router = APIRouter(tags=["Models"])


@router.get("/models/base", response_model=Dict[str, Union[List[BaseModelResponse], Pagination]])
async def list_base_models(
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[BaseModelResponse], Pagination]]:
    """List all available base LLM models."""
    models, pagination = await get_base_models(db, page, items_per_page)
    return {
        "data": models,
        "pagination": pagination
    }


@router.get("/models/base/{model_name}", response_model=BaseModelResponse)
async def get_base_model_details(
        model_name: str,
        db: AsyncSession = Depends(get_db),
) -> BaseModelResponse:
    """Get detailed information about a specific base model."""
    model = await get_base_model(db, model_name)
    if not model:
        raise HTTPException(status_code=404, detail="Base model not found")
    return model


@router.get("/models/fine-tuned", response_model=Dict[str, Union[List[FineTunedModelResponse], Pagination]])
async def list_fine_tuned_models(
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[FineTunedModelResponse], Pagination]]:
    """List all fine-tuned models for the current user."""
    models, pagination = await get_fine_tuned_models(db, current_user.id, page, items_per_page)
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
    """Get detailed information about a specific fine-tuned model."""
    model = await get_fine_tuned_model(db, current_user.id, model_name)
    if not model:
        raise HTTPException(status_code=404, detail="Fine-tuned model not found")
    return model
