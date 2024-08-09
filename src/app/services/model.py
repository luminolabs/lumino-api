from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base_model import BaseModel
from app.models.fine_tuned_model import FineTunedModel
from app.schemas.model import BaseModelResponse, FineTunedModelResponse, FineTunedModelCreate, FineTunedModelUpdate


async def get_base_models(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[BaseModelResponse]:
    """Get all available base LLM models."""
    result = await db.execute(
        select(BaseModel)
        .offset(skip)
        .limit(limit)
    )
    return [BaseModelResponse.from_orm(model) for model in result.scalars().all()]


async def get_base_model(db: AsyncSession, model_id: UUID) -> BaseModelResponse | None:
    """Get a specific base model."""
    model = await db.get(BaseModel, model_id)
    if model:
        return BaseModelResponse.from_orm(model)
    return None


async def get_fine_tuned_models(db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100) -> list[FineTunedModelResponse]:
    """Get all fine-tuned models for a user."""
    result = await db.execute(
        select(FineTunedModel)
        .where(FineTunedModel.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return [FineTunedModelResponse.from_orm(model) for model in result.scalars().all()]


async def get_fine_tuned_model(db: AsyncSession, model_id: UUID) -> FineTunedModelResponse | None:
    """Get a specific fine-tuned model."""
    model = await db.get(FineTunedModel, model_id)
    if model:
        return FineTunedModelResponse.from_orm(model)
    return None


async def create_fine_tuned_model(db: AsyncSession, user_id: UUID, model: FineTunedModelCreate) -> FineTunedModelResponse:
    """Create a new fine-tuned model."""
    db_model = FineTunedModel(
        user_id=user_id,
        fine_tuning_job_id=model.fine_tuning_job_id,
        description=model.description
    )
    db.add(db_model)
    await db.commit()
    await db.refresh(db_model)
    return FineTunedModelResponse.from_orm(db_model)


async def update_fine_tuned_model(db: AsyncSession, model_id: UUID, model_update: FineTunedModelUpdate) -> FineTunedModelResponse:
    """Update a fine-tuned model."""
    db_model = await db.get(FineTunedModel, model_id)
    if not db_model:
        raise ValueError("Fine-tuned model not found")

    update_data = model_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_model, field, value)

    await db.commit()
    await db.refresh(db_model)
    return FineTunedModelResponse.from_orm(db_model)


async def delete_fine_tuned_model(db: AsyncSession, model_id: UUID) -> None:
    """Delete a fine-tuned model."""
    db_model = await db.get(FineTunedModel, model_id)
    if not db_model:
        raise ValueError("Fine-tuned model not found")

    await db.delete(db_model)
    await db.commit()
