from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetCreate, DatasetResponse, DatasetUpdate
from app.core.storage import upload_file, delete_file, get_file_stream


async def create_dataset(db: AsyncSession, user_id: UUID, dataset: DatasetCreate) -> DatasetResponse:
    """Create a new dataset."""
    storage_url = await upload_file(dataset.file, f"datasets/{user_id}/")

    db_dataset = Dataset(
        id=dataset.id,
        user_id=user_id,
        description=dataset.description,
        storage_url=storage_url,
        file_size=dataset.file.size,
        status="uploaded"
    )
    db.add(db_dataset)
    await db.commit()
    await db.refresh(db_dataset)

    return DatasetResponse.from_orm(db_dataset)


async def get_datasets(db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100) -> list[DatasetResponse]:
    """Get all datasets for a user."""
    result = await db.execute(
        select(Dataset)
        .where(Dataset.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return [DatasetResponse.from_orm(dataset) for dataset in result.scalars().all()]


async def get_dataset(db: AsyncSession, dataset_id: UUID) -> DatasetResponse | None:
    """Get a specific dataset."""
    dataset = await db.get(Dataset, dataset_id)
    if dataset:
        return DatasetResponse.from_orm(dataset)
    return None


async def update_dataset(db: AsyncSession, dataset_id: UUID, dataset_update: DatasetUpdate) -> DatasetResponse:
    """Update a dataset."""
    db_dataset = await db.get(Dataset, dataset_id)
    if not db_dataset:
        raise ValueError("Dataset not found")

    update_data = dataset_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_dataset, field, value)

    await db.commit()
    await db.refresh(db_dataset)
    return DatasetResponse.from_orm(db_dataset)


async def delete_dataset(db: AsyncSession, dataset_id: UUID) -> None:
    """Delete a dataset."""
    db_dataset = await db.get(Dataset, dataset_id)
    if not db_dataset:
        raise ValueError("Dataset not found")

    await delete_file(db_dataset.storage_url)
    await db.delete(db_dataset)
    await db.commit()


async def download_dataset(db: AsyncSession, dataset_id: UUID):
    """Get a file stream for downloading a dataset."""
    db_dataset = await db.get(Dataset, dataset_id)
    if not db_dataset:
        raise ValueError("Dataset not found")

    return await get_file_stream(db_dataset.storage_url)
