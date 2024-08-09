from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.model import BaseModelResponse, FineTunedModelResponse
from app.services.model import (
    get_base_models,
    get_base_model,
    get_fine_tuned_models,
    get_fine_tuned_model,
)
from app.services.user import get_current_user

router = APIRouter(tags=["Models"])


@router.get("/models/base", response_model=list[BaseModelResponse])
async def list_base_models(
        db: AsyncSession = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
) -> list[BaseModelResponse]:
    """List all available base LLM models."""
    return await get_base_models(db, skip, limit)


@router.get("/models/base/{model_id}", response_model=BaseModelResponse)
async def get_base_model_details(
        model_id: UUID,
        db: AsyncSession = Depends(get_db),
) -> BaseModelResponse:
    """Get detailed information about a specific base model."""
    model = await get_base_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Base model not found")
    return model


@router.get("/models/me", response_model=list[FineTunedModelResponse])
async def list_fine_tuned_models(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
) -> list[FineTunedModelResponse]:
    """List all fine-tuned models for the current user."""
    return await get_fine_tuned_models(db, current_user["id"], skip, limit)


@router.get("/models/me/{model_id}", response_model=FineTunedModelResponse)
async def get_fine_tuned_model_details(
        model_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> FineTunedModelResponse:
    """Get detailed information about a specific fine-tuned model."""
    model = await get_fine_tuned_model(db, model_id)
    if not model or model.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Fine-tuned model not found")
    return model
