import math
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base_model import BaseModel
from app.models.fine_tuned_model import FineTunedModel
from app.schemas.common import Pagination
from app.schemas.model import BaseModelResponse, FineTunedModelResponse


async def get_base_models(
        db: AsyncSession,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[BaseModelResponse], Pagination]:
    """Get all available base LLM models with pagination."""
    total_count = await db.scalar(select(func.count()).select_from(BaseModel))

    total_pages = math.ceil(total_count / items_per_page)
    offset = (page - 1) * items_per_page

    result = await db.execute(
        select(BaseModel)
        .offset(offset)
        .limit(items_per_page)
    )
    models = [BaseModelResponse.from_orm(model) for model in result.scalars().all()]

    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None
    )

    return models, pagination


async def get_base_model(db: AsyncSession, model_name: str) -> BaseModelResponse | None:
    """Get a specific base model."""
    result = await db.execute(
        select(BaseModel)
        .where(BaseModel.name == model_name)
    )
    model = result.scalar_one_or_none()
    if model:
        return BaseModelResponse.from_orm(model)
    return None


async def get_fine_tuned_models(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[FineTunedModelResponse], Pagination]:
    """Get all fine-tuned models for a user with pagination."""
    total_count = await db.scalar(
        select(func.count()).select_from(FineTunedModel).where(FineTunedModel.user_id == user_id)
    )

    total_pages = math.ceil(total_count / items_per_page)
    offset = (page - 1) * items_per_page

    result = await db.execute(
        select(FineTunedModel)
        .where(FineTunedModel.user_id == user_id)
        .offset(offset)
        .limit(items_per_page)
    )
    models = [FineTunedModelResponse.from_orm(model) for model in result.scalars().all()]

    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None
    )

    return models, pagination


async def get_fine_tuned_model(db: AsyncSession, user_id: UUID, model_name: str) -> FineTunedModelResponse | None:
    """Get a specific fine-tuned model."""
    result = await db.execute(
        select(FineTunedModel)
        .where(FineTunedModel.user_id == user_id, FineTunedModel.name == model_name)
    )
    model = result.scalar_one_or_none()
    if model:
        return FineTunedModelResponse.from_orm(model)
    return None
