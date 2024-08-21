import math
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.constants import DatasetStatus
from app.core.exceptions import (
    DatasetAlreadyExistsError,
    DatasetNotFoundError,
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
        DatasetAlreadyExistsError: If a dataset with the same name already exists for the user.
        SQLAlchemyError: If there's an error committing the transaction.
    """
    # Check if a dataset with the same name already exists for this user
    dataset_exists = (await db.execute(
        select(Dataset).where(
            (Dataset.user_id == user_id) & (Dataset.name == dataset.name)
        )
    )).scalar_one_or_none() is not None
    if dataset_exists:
        raise DatasetAlreadyExistsError(f"A dataset with the name '{dataset.name}' already "
                                        f"exists for user {user_id}", logger)

    # Upload the dataset file to storage
    file_name = await upload_file(config.gcs_datasets_path, dataset.file, user_id)

    # Insert the dataset in the database
    db_dataset = Dataset(
        user_id=user_id,
        name=dataset.name,
        description=dataset.description,
        file_name=file_name,
        file_size=dataset.file.size,
        status=DatasetStatus.UPLOADED
    )
    db.add(db_dataset)

    try:
        # Commit the transaction
        await db.commit()
    except SQLAlchemyError as e:
        # If there's an SQL error, delete the file from storage
        await delete_file(config.gcs_datasets_path, file_name, user_id)
        raise e

    logger.info(f"Successfully created dataset: {db_dataset.id} for user: {user_id}")
    return DatasetResponse.from_orm(db_dataset)


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
    # Count the total items
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
    )

    logger.info(f"Retrieved datasets for user: {user_id}, page: {page}")
    return datasets, pagination


async def get_dataset(db: AsyncSession, user_id: UUID, dataset_name: str) -> DatasetResponse:
    """
    Get a specific dataset.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        dataset_name (str): The name of the dataset.

    Returns:
        DatasetResponse: The dataset information if found, None otherwise.

    Raises:
        DatasetNotFoundError: If the dataset is not found.
    """
    # Get the dataset from the database
    dataset = (await db.execute(
        select(Dataset)
        .where(Dataset.user_id == user_id, Dataset.name == dataset_name)
    )).scalar_one_or_none()
    
    # Raise an error if the dataset is not found
    if not dataset:
        raise DatasetNotFoundError(f"Dataset not found: {dataset_name} for user: {user_id}", logger)
    
    # Log and return the dataset
    logger.info(f"Retrieved dataset: {dataset_name} for user: {user_id}")
    return DatasetResponse.from_orm(dataset)


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
    """
    # Get the dataset from the database
    db_dataset = (await db.execute(
        select(Dataset)
        .where(Dataset.user_id == user_id, Dataset.name == dataset_name)
    )).scalar_one_or_none()
    
    # Raise an error if the dataset is not found
    if not db_dataset:
        raise DatasetNotFoundError(f"Dataset not found: {dataset_name} for user: {user_id}", logger)

    # Update the dataset fields
    update_data = dataset_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_dataset, field, value)
    
    # Store the updated dataset in the database
    await db.commit()
    
    # Log and return the updated dataset
    logger.info(f"Successfully updated dataset: {dataset_name} for user: {user_id}")
    return DatasetResponse.from_orm(db_dataset)


async def mark_dataset_deleted(db: AsyncSession, user_id: UUID, dataset_name: str) -> None:
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
    # Get the dataset from the database
    db_dataset = (await db.execute(
        select(Dataset)
        .where(Dataset.user_id == user_id, Dataset.name == dataset_name)
    )).scalar_one_or_none()

    # Raise an error if the dataset is not found
    if not db_dataset:
        raise DatasetNotFoundError(f"Dataset not found: {dataset_name} for user: {user_id}", logger)

    # Delete the dataset from the storage
    await delete_file(config.gcs_datasets_path, db_dataset.file_name, user_id)
    
    # Delete the dataset from the database
    db_dataset.status = DatasetStatus.DELETED
    await db.commit()
    
    logger.info(f"Successfully deleted dataset: {dataset_name} for user: {user_id}")
