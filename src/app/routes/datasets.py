from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.dataset import DatasetCreate, DatasetResponse
from app.schemas.user import UserResponse
from app.services.dataset import (
    create_dataset,
    get_datasets,
    get_dataset,
    delete_dataset,
    download_dataset,
)
from app.services.user import get_current_user

router = APIRouter(tags=["Datasets"])


@router.post("/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
        file: UploadFile = File(...),
        dataset_id: str | None = None,
        description: str | None = None,
        current_user: UserResponse = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """
    Upload a new dataset file.

    Args:
        file (UploadFile): The dataset file to upload.
        dataset_id (str, optional): User-assigned name for the dataset.
        description (str, optional): User-provided description of the dataset.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        DatasetResponse: The created dataset's data.

    Raises:
        HTTPException: If there's an error creating the dataset.
    """
    try:
        dataset_create = DatasetCreate(
            id=dataset_id,
            description=description,
            file=file,
        )
        return await create_dataset(db, current_user.id, dataset_create)  # Use dot notation here
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
) -> list[DatasetResponse]:
    """
    List all datasets uploaded by the user.

    Args:
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.
        skip (int): The number of items to skip (for pagination).
        limit (int): The maximum number of items to return (for pagination).

    Returns:
        list[DatasetResponse]: A list of datasets belonging to the current user.
    """
    return await get_datasets(db, current_user["id"], skip, limit)


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset_info(
        dataset_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> DatasetResponse:
    """
    Get information about a specific dataset.

    Args:
        dataset_id (UUID): The ID of the dataset to retrieve.
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        DatasetResponse: The requested dataset's data.

    Raises:
        HTTPException: If the dataset is not found or doesn't belong to the current user.
    """
    dataset = await get_dataset(db, dataset_id)
    if not dataset or dataset.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset_file(
        dataset_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a specific dataset file.

    Args:
        dataset_id (UUID): The ID of the dataset to delete.
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the dataset is not found, doesn't belong to the current user, or if there's an error deleting it.
    """
    dataset = await get_dataset(db, dataset_id)
    if not dataset or dataset.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Dataset not found")
    try:
        await delete_dataset(db, dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/datasets/{dataset_id}/download")
async def download_dataset_file(
        dataset_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Download a specific dataset file.

    Args:
        dataset_id (UUID): The ID of the dataset to download.
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        StreamingResponse: A streaming response containing the dataset file.

    Raises:
        HTTPException: If the dataset is not found or doesn't belong to the current user.
    """
    dataset = await get_dataset(db, dataset_id)
    if not dataset or dataset.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        file_stream = await download_dataset(db, dataset_id)
        return StreamingResponse(
            file_stream,
            media_type="application/jsonl",
            headers={"Content-Disposition": f"attachment; filename={dataset.id}.jsonl"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
