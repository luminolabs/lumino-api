from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset


async def get_dataset_by_name(db: AsyncSession, user_id: UUID, name: str) -> Optional[Dataset]:
    """Get a dataset by name for a specific user."""
    result = await db.execute(
        select(Dataset).where(Dataset.user_id == user_id, Dataset.name == name)
    )
    return result.scalar_one_or_none()


async def list_datasets(db: AsyncSession, user_id: UUID, offset: int, limit: int) -> List[Dataset]:
    """List datasets for a specific user with pagination."""
    result = await db.execute(
        select(Dataset)
        .where(Dataset.user_id == user_id)
        .order_by(Dataset.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


async def count_datasets(db: AsyncSession, user_id: UUID) -> int:
    """Count total datasets for a specific user."""
    result = await db.execute(
        select(func.count()).select_from(Dataset).where(Dataset.user_id == user_id)
    )
    return result.scalar_one()
