from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.common import sanitize_filename
from app.core.config_manager import config
from app.core.constants import DatasetStatus
from app.core.exceptions import (
    DatasetAlreadyExistsError,
    DatasetNotFoundError,
)
from app.core.storage import upload_file, delete_file
from app.core.utils import setup_logger
from app.models.dataset import Dataset
from app.queries import datasets as dataset_queries
from app.schemas.common import Pagination
from app.schemas.dataset import DatasetCreate, DatasetResponse, DatasetUpdate

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


def get_dataset_bucket() -> str:
    """Get the dataset bucket."""
    return f'lum-{config.env_name}-{config.gcs_datasets_bucket}'


async def create_dataset(db: AsyncSession, user_id: UUID, dataset: DatasetCreate) -> DatasetResponse:
    """Create a new dataset."""
    # Check if a dataset with the same name already exists
    existing_dataset = await dataset_queries.get_dataset_by_name(db, user_id, dataset.name)
    if existing_dataset:
        raise DatasetAlreadyExistsError(f"A dataset with the name '{dataset.name}' already "
                                        f"exists for user {user_id}", logger)

    # Sanitize the filename
    original_filename = dataset.file.filename
    sanitized_filename = sanitize_filename(original_filename)
    dataset.file.filename = sanitized_filename

    # Upload the dataset file to storage
    file_name = await upload_file(get_dataset_bucket(), '', dataset.file, user_id)

    try:
        # Create the dataset record
        db_dataset = Dataset(
            user_id=user_id,
            name=dataset.name,
            description=dataset.description,
            file_name=file_name,
            file_size=dataset.file.size,
            status=DatasetStatus.UPLOADED
        )
        db.add(db_dataset)
        await db.commit()
        await db.refresh(db_dataset)

        logger.info(f"Created dataset: {db_dataset.id} for user: {user_id}")
        return DatasetResponse.from_orm(db_dataset)

    except SQLAlchemyError as e:
        # If there's an SQL error, delete the uploaded file
        await delete_file(get_dataset_bucket(), '', file_name, user_id)
        await db.rollback()
        raise e


async def get_datasets(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[DatasetResponse], Pagination]:
    """Get all datasets for a user with pagination."""
    offset = (page - 1) * items_per_page

    # Get total count and paginated results
    total_count = await dataset_queries.count_datasets(db, user_id)
    datasets = await dataset_queries.list_datasets(db, user_id, offset, items_per_page)

    # Calculate pagination
    total_pages = (total_count + items_per_page - 1) // items_per_page
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
    )

    # Create response objects
    dataset_responses = [DatasetResponse.from_orm(dataset) for dataset in datasets]

    logger.info(f"Retrieved datasets for user: {user_id}, page: {page}")
    return dataset_responses, pagination


async def get_dataset(db: AsyncSession, user_id: UUID, dataset_name: str) -> DatasetResponse:
    """Get a specific dataset."""
    dataset = await dataset_queries.get_dataset_by_name(db, user_id, dataset_name)
    if not dataset:
        raise DatasetNotFoundError(f"Dataset not found: {dataset_name} for user: {user_id}", logger)

    logger.info(f"Retrieved dataset: {dataset_name} for user: {user_id}")
    return DatasetResponse.from_orm(dataset)


async def update_dataset(db: AsyncSession, user_id: UUID, dataset_name: str,
                         dataset_update: DatasetUpdate) -> DatasetResponse:
    """Update a dataset."""
    db_dataset = await dataset_queries.get_dataset_by_name(db, user_id, dataset_name)
    if not db_dataset:
        raise DatasetNotFoundError(f"Dataset not found: {dataset_name} for user: {user_id}", logger)

    new_db_dataset = await dataset_queries.get_dataset_by_name(db, user_id, dataset_update.name)
    if new_db_dataset:
        raise DatasetAlreadyExistsError(f"A dataset with the name '{dataset_update.name}' already "
                                        f"exists for user {user_id}", logger)

    # Update the dataset fields
    update_data = dataset_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_dataset, field, value)

    await db.commit()
    await db.refresh(db_dataset)

    logger.info(f"Updated dataset: {dataset_name} for user: {user_id}")
    return DatasetResponse.from_orm(db_dataset)


async def delete_dataset(db: AsyncSession, user_id: UUID, dataset_name: str) -> None:
    """Delete a dataset."""
    db_dataset = await dataset_queries.get_dataset_by_name(db, user_id, dataset_name)
    if not db_dataset:
        raise DatasetNotFoundError(f"Dataset not found: {dataset_name} for user: {user_id}", logger)

    try:
        # Delete the file from storage first
        await delete_file(get_dataset_bucket(), '', db_dataset.file_name, user_id)

        # Mark the dataset as deleted in the database
        db_dataset.status = DatasetStatus.DELETED
        await db.commit()

        logger.info(f"Deleted dataset: {dataset_name} for user: {user_id}")
    except Exception as e:
        await db.rollback()
        raise e
