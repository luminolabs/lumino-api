from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DatasetStatus
from app.models.dataset import Dataset
from app.schemas.common import Pagination
from app.schemas.dataset import DatasetCreate, DatasetResponse, DatasetUpdate
from app.core.storage import upload_file, delete_file, get_file_stream


async def create_dataset(db: AsyncSession, user_id: UUID, dataset: DatasetCreate) -> DatasetResponse:
    """Create a new dataset."""
    storage_url = await upload_file(dataset.file, f"datasets/{user_id}/")

    db_dataset = Dataset(
        user_id=user_id,
        name=dataset.name,
        description=dataset.description,
        storage_url=storage_url,
        file_size=dataset.file.size,
        status=DatasetStatus.UPLOADED
    )
    db.add(db_dataset)
    await db.commit()
    await db.refresh(db_dataset)

    return DatasetResponse.from_orm(db_dataset)


async def get_datasets(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[DatasetResponse], Pagination]:
    """Get all datasets for a user with pagination."""
    # Count total items
    total_count = await db.scalar(
        select(func.count()).select_from(Dataset).where(Dataset.user_id == user_id)
    )

    # Calculate pagination
    total_pages = math.ceil(total_count / items_per_page)
    offset = (page - 1) * items_per_page

    # Fetch items
    result = await db.execute(
        select(Dataset)
        .where(Dataset.user_id == user_id)
        .offset(offset)
        .limit(items_per_page)
    )
    datasets = [DatasetResponse.from_orm(dataset) for dataset in result.scalars().all()]

    # Create pagination object
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None
    )

    return datasets, pagination


async def get_dataset(db: AsyncSession, user_id: UUID, dataset_name: str) -> DatasetResponse | None:
    """Get a specific dataset."""
    result = await db.execute(
        select(Dataset)
        .where(Dataset.user_id == user_id, Dataset.name == dataset_name)
    )
    dataset = result.scalar_one_or_none()
    if dataset:
        return DatasetResponse.from_orm(dataset)
    return None


async def update_dataset(db: AsyncSession, user_id: UUID, dataset_name: str, dataset_update: DatasetUpdate) -> DatasetResponse:
    """Update a dataset."""
    result = await db.execute(
        select(Dataset)
        .where(Dataset.user_id == user_id, Dataset.name == dataset_name)
    )
    db_dataset = result.scalar_one_or_none()
    if not db_dataset:
        raise ValueError("Dataset not found")

    update_data = dataset_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_dataset, field, value)

    await db.commit()
    await db.refresh(db_dataset)
    return DatasetResponse.from_orm(db_dataset)


async def delete_dataset(db: AsyncSession, user_id: UUID, dataset_name: str) -> None:
    """Delete a dataset."""
    result = await db.execute(
        select(Dataset)
        .where(Dataset.user_id == user_id, Dataset.name == dataset_name)
    )
    db_dataset = result.scalar_one_or_none()
    if not db_dataset:
        raise ValueError("Dataset not found")

    await delete_file(db_dataset.storage_url)
    await db.delete(db_dataset)
    await db.commit()


async def download_dataset(db: AsyncSession, user_id: UUID, dataset_name: str):
    """Get a file stream for downloading a dataset."""
    result = await db.execute(
        select(Dataset)
        .where(Dataset.user_id == user_id, Dataset.name == dataset_name)
    )
    db_dataset = result.scalar_one_or_none()
    if not db_dataset:
        raise ValueError("Dataset not found")

    file_stream = await get_file_stream(db_dataset.storage_url)
    return db_dataset, file_stream
