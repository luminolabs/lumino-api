from typing import Dict, Union, List

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.params import Query, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
    download_dataset,
)
from app.core.authentication import get_current_active_user

router = APIRouter(tags=["Datasets"])


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
    """
    try:
        dataset_create = DatasetCreate(
            name=name,
            description=description,
            file=file,
        )
        return await create_dataset(db, current_user.id, dataset_create)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/datasets", response_model=Dict[str, Union[List[DatasetResponse], Pagination]])
async def list_datasets(
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> dict:
    """
    List all datasets uploaded by the user.
    """
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
    """
    dataset = await get_dataset(db, current_user.id, dataset_name)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
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
    """
    try:
        return await update_dataset(db, current_user.id, dataset_name, dataset_update)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/datasets/{dataset_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset_file(
        dataset_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a specific dataset file.
    """
    try:
        await delete_dataset(db, current_user.id, dataset_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/datasets/{dataset_name}/download")
async def download_dataset_file(
        dataset_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Download a specific dataset file.
    """
    try:
        dataset, file_stream = await download_dataset(db, current_user.id, dataset_name)
        return StreamingResponse(
            file_stream,
            media_type="application/jsonl",
            headers={"Content-Disposition": f"attachment; filename={dataset.name}.jsonl"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
