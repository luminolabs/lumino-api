from typing import Dict, Union, List

from fastapi import APIRouter, Depends, status, UploadFile, File
from fastapi.params import Query, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import get_current_active_user
from app.core.config_manager import config
from app.core.database import get_db
from app.core.utils import setup_logger
from app.models.user import User
from app.schemas.common import Pagination
from app.schemas.dataset import DatasetCreate, DatasetResponse, DatasetUpdate
from app.services.dataset import (
    create_dataset,
    get_datasets,
    get_dataset,
    update_dataset,
    delete_dataset,
)

# Set up API router
router = APIRouter(tags=["Datasets"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.post("/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
        file: UploadFile = File(...),
        name: str = Form(...),
        description: str = Form(None),
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """Upload a new dataset file."""
    dataset_create = DatasetCreate(
        name=name,
        description=description,
        file=file,
    )
    return await create_dataset(db, current_user.id, dataset_create)


@router.get("/datasets", response_model=Dict[str, Union[List[DatasetResponse], Pagination]])
async def list_datasets(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[DatasetResponse], Pagination]]:
    """List all datasets uploaded by the user."""
    datasets, pagination = await get_datasets(db, current_user.id, page, items_per_page)
    return {
        "data": datasets,
        "pagination": pagination
    }


@router.get("/datasets/{dataset_name}", response_model=DatasetResponse)
async def get_dataset_info(
        dataset_name: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """Get information about a specific dataset."""
    return await get_dataset(db, current_user.id, dataset_name)


@router.patch("/datasets/{dataset_name}", response_model=DatasetResponse)
async def update_dataset_info(
        dataset_name: str,
        dataset_update: DatasetUpdate,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """Update a specific dataset's information."""
    return await update_dataset(db, current_user.id, dataset_name, dataset_update)


@router.delete("/datasets/{dataset_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset_file(
        dataset_name: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a specific dataset file."""
    await delete_dataset(db, current_user.id, dataset_name)
