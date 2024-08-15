import math
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.constants import DatasetStatus
from app.core.exceptions import (
    DatasetCreationError,
    DatasetNotFoundError,
    DatasetUpdateError,
    DatasetDeletionError
)
from app.models.dataset import Dataset
from app.schemas.common import Pagination
from app.schemas.dataset import DatasetCreate, DatasetResponse, DatasetUpdate
from app.core.storage import upload_file, delete_file
from app.utils import setup_logger

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def create_dataset(db: AsyncSession, user_id: UUID, dataset: DatasetCreate) -> DatasetResponse:
    """
    Create a new dataset.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user creating the dataset.
        dataset (DatasetCreate): The dataset creation data.

    Returns:
        DatasetResponse: The created dataset information.

    Raises:
        DatasetCreationError: If there's an error creating the dataset.
    """
    try:
        # Check if a dataset with the same name already exists for this user
        existing_dataset = await db.execute(
            select(Dataset).where(
                (Dataset.user_id == user_id) & (Dataset.name == dataset.name)
            )
        )
        if existing_dataset.scalar_one_or_none():
            logger.warning(f"Attempt to create duplicate dataset '{dataset.name}' for user {user_id}")
            raise DatasetCreationError(f"A dataset with the name '{dataset.name}' already exists for this user.")

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

        logger.info(f"Successfully created dataset: {db_dataset.id} for user: {user_id}")
        return DatasetResponse.from_orm(db_dataset)
    except DatasetCreationError:
        raise
    except Exception as e:
        logger.error(f"Error creating dataset for user {user_id}: {e.detail}")
        await db.rollback()
        # Delete the uploaded file if there was an error
        if 'storage_url' in locals():
            await delete_file(storage_url)
        raise DatasetCreationError(f"Failed to create dataset: {e.detail}")


async def get_datasets(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[DatasetResponse], Pagination]:
    """
    Get all datasets for a user with pagination.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        tuple[list[DatasetResponse], Pagination]: A tuple containing the list of datasets and pagination info.
    """
    try:
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

        logger.info(f"Retrieved datasets for user: {user_id}, page: {page}")
        return datasets, pagination
    except Exception as e:
        logger.error(f"Error retrieving datasets for user {user_id}: {e.detail}")
        raise


async def get_dataset(db: AsyncSession, user_id: UUID, dataset_name: str) -> DatasetResponse | None:
    """
    Get a specific dataset.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        dataset_name (str): The name of the dataset.

    Returns:
        DatasetResponse | None: The dataset information if found, None otherwise.
    """
    try:
        result = await db.execute(
            select(Dataset)
            .where(Dataset.user_id == user_id, Dataset.name == dataset_name)
        )
        dataset = result.scalar_one_or_none()
        if dataset:
            logger.info(f"Retrieved dataset: {dataset_name} for user: {user_id}")
            return DatasetResponse.from_orm(dataset)
        logger.warning(f"Dataset not found: {dataset_name} for user: {user_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving dataset {dataset_name} for user {user_id}: {e.detail}")
        raise


async def update_dataset(db: AsyncSession, user_id: UUID, dataset_name: str, dataset_update: DatasetUpdate) -> DatasetResponse:
    """
    Update a dataset.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        dataset_name (str): The name of the dataset to update.
        dataset_update (DatasetUpdate): The update data for the dataset.

    Returns:
        DatasetResponse: The updated dataset information.

    Raises:
        DatasetNotFoundError: If the dataset is not found.
        DatasetUpdateError: If there's an error updating the dataset.
    """
    try:
        result = await db.execute(
            select(Dataset)
            .where(Dataset.user_id == user_id, Dataset.name == dataset_name)
        )
        db_dataset = result.scalar_one_or_none()
        if not db_dataset:
            logger.warning(f"Dataset not found for update: {dataset_name} for user: {user_id}")
            raise DatasetNotFoundError("Dataset not found")

        update_data = dataset_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_dataset, field, value)

        await db.commit()
        logger.info(f"Successfully updated dataset: {dataset_name} for user: {user_id}")
        return DatasetResponse.from_orm(db_dataset)
    except DatasetNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error updating dataset {dataset_name} for user {user_id}: {e.detail}")
        await db.rollback()
        raise DatasetUpdateError(f"Failed to update dataset: {e.detail}")


async def delete_dataset(db: AsyncSession, user_id: UUID, dataset_name: str) -> None:
    """
    Delete a dataset.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        dataset_name (str): The name of the dataset to delete.

    Raises:
        DatasetNotFoundError: If the dataset is not found.
        DatasetDeletionError: If there's an error deleting the dataset.
    """
    try:
        result = await db.execute(
            select(Dataset)
            .where(Dataset.user_id == user_id, Dataset.name == dataset_name)
        )
        db_dataset = result.scalar_one_or_none()
        if not db_dataset:
            logger.warning(f"Dataset not found for deletion: {dataset_name} for user: {user_id}")
            raise DatasetNotFoundError("Dataset not found")

        await delete_file(db_dataset.storage_url)
        await db.delete(db_dataset)
        await db.commit()
        logger.info(f"Successfully deleted dataset: {dataset_name} for user: {user_id}")
    except DatasetNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting dataset {dataset_name} for user {user_id}: {e.detail}")
        await db.rollback()
        raise DatasetDeletionError(f"Failed to delete dataset: {e.detail}")