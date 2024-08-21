from typing import Dict, Union, List

from fastapi import APIRouter, Depends, status, UploadFile, File
from fastapi.params import Query, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.core.authentication import get_current_active_user
from app.core.exceptions import (
    BadRequestError,
    NotFoundError,
    DatasetCreationError,
    DatasetNotFoundError,
    DatasetUpdateError,
    DatasetDeletionError
)
from app.database import get_db
from app.schemas.common import Pagination
from app.schemas.dataset import DatasetCreate, DatasetResponse, DatasetUpdate
from app.schemas.user import UserResponse
from app.services.dataset import (
    create_dataset,
    get_datasets,
    get_dataset,
    update_dataset,
    delete_dataset,
)
from app.utils import setup_logger

router = APIRouter(tags=["Datasets"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.post("/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
        file: UploadFile = File(...),
        name: str = Form(None),
        description: str = Form(None),
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """
    Upload a new dataset file.

    Args:
        file (UploadFile): The dataset file to be uploaded.
        name (str, optional): The name of the dataset.
        description (str, optional): A description of the dataset.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        DatasetResponse: The created dataset information.

    Raises:
        DatasetCreationError: If there's an error creating the dataset.
    """
    try:
        logger.info(f"Attempting to create dataset for user: {current_user.id}")
        dataset_create = DatasetCreate(
            name=name,
            description=description,
            file=file,
        )
        new_dataset = await create_dataset(db, current_user.id, dataset_create)
        logger.info(f"Successfully created dataset: {new_dataset.id} for user: {current_user.id}")
        return new_dataset
    except DatasetCreationError as e:
        logger.error(f"Error creating dataset for user {current_user.id}: {e.detail}")
        raise BadRequestError(e.detail)


@router.get("/datasets", response_model=Dict[str, Union[List[DatasetResponse], Pagination]])
async def list_datasets(
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[DatasetResponse], Pagination]]:
    """
    List all datasets uploaded by the user.

    Args:
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        Dict[str, Union[List[DatasetResponse], Pagination]]: A dictionary containing the list of datasets and pagination info.
    """
    logger.info(f"Fetching datasets for user: {current_user.id}")
    datasets, pagination = await get_datasets(db, current_user.id, page, items_per_page)
    return {
        "data": datasets,
        "pagination": pagination
    }


@router.get("/datasets/{dataset_name}", response_model=DatasetResponse)
async def get_dataset_info(
        dataset_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """
    Get information about a specific dataset.

    Args:
        dataset_name (str): The name of the dataset.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        DatasetResponse: The dataset information.

    Raises:
        DatasetNotFoundError: If the dataset is not found.
    """
    logger.info(f"Fetching dataset info for user: {current_user.id}, dataset name: {dataset_name}")
    dataset = await get_dataset(db, current_user.id, dataset_name)
    if not dataset:
        logger.warning(f"Dataset not found for user: {current_user.id}, dataset name: {dataset_name}")
        raise DatasetNotFoundError("Dataset not found")
    return dataset


@router.patch("/datasets/{dataset_name}", response_model=DatasetResponse)
async def update_dataset_info(
        dataset_name: str,
        dataset_update: DatasetUpdate,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """
    Update a specific dataset's information.

    Args:
        dataset_name (str): The name of the dataset to update.
        dataset_update (DatasetUpdate): The update data for the dataset.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        DatasetResponse: The updated dataset information.

    Raises:
        DatasetNotFoundError: If the dataset is not found.
        DatasetUpdateError: If there's an error updating the dataset.
    """
    try:
        logger.info(f"Updating dataset for user: {current_user.id}, dataset name: {dataset_name}")
        updated_dataset = await update_dataset(db, current_user.id, dataset_name, dataset_update)
        logger.info(f"Successfully updated dataset for user: {current_user.id}, dataset name: {dataset_name}")
        return updated_dataset
    except DatasetNotFoundError as e:
        logger.error(f"Dataset not found for user {current_user.id}, dataset name {dataset_name}: {e.detail}")
        raise NotFoundError(e.detail)
    except DatasetUpdateError as e:
        logger.error(f"Error updating dataset for user {current_user.id}, dataset name {dataset_name}: {e.detail}")
        raise BadRequestError(e.detail)


@router.delete("/datasets/{dataset_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset_file(
        dataset_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a specific dataset file.

    Args:
        dataset_name (str): The name of the dataset to delete.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Raises:
        DatasetNotFoundError: If the dataset is not found.
        DatasetDeletionError: If there's an error deleting the dataset.
    """
    try:
        logger.info(f"Deleting dataset for user: {current_user.id}, dataset name: {dataset_name}")
        await delete_dataset(db, current_user.id, dataset_name)
        logger.info(f"Successfully deleted dataset for user: {current_user.id}, dataset name: {dataset_name}")
    except DatasetNotFoundError as e:
        logger.error(f"Dataset not found for user {current_user.id}, dataset name {dataset_name}: {e.detail}")
        raise NotFoundError(e.detail)
    except DatasetDeletionError as e:
        logger.error(f"Error deleting dataset for user {current_user.id}, dataset name {dataset_name}: {e.detail}")
        raise BadRequestError(e.detail)