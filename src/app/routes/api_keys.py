from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyUpdate
from app.services.api_key import (
    create_api_key,
    get_api_keys,
    get_api_key,
    update_api_key,
    delete_api_key,
)
from app.services.user import get_current_user

router = APIRouter(tags=["API Keys"])


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_new_api_key(
        api_key: ApiKeyCreate,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Create a new API key for the current user.

    Args:
        api_key (ApiKeyCreate): The API key data for creation.
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ApiKeyResponse: The created API key's data.

    Raises:
        HTTPException: If there's an error creating the API key.
    """
    try:
        return await create_api_key(db, current_user["id"], api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
) -> list[ApiKeyResponse]:
    """
    List all API keys for the current user.

    Args:
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.
        skip (int): The number of items to skip (for pagination).
        limit (int): The maximum number of items to return (for pagination).

    Returns:
        list[ApiKeyResponse]: A list of API keys belonging to the current user.
    """
    return await get_api_keys(db, current_user["id"], skip, limit)


@router.get("/api-keys/{key_id}", response_model=ApiKeyResponse)
async def get_api_key_details(
        key_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Get details of a specific API key.

    Args:
        key_id (UUID): The ID of the API key to retrieve.
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ApiKeyResponse: The requested API key's data.

    Raises:
        HTTPException: If the API key is not found or doesn't belong to the current user.
    """
    api_key = await get_api_key(db, key_id)
    if not api_key or api_key.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="API key not found")
    return api_key


@router.patch("/api-keys/{key_id}", response_model=ApiKeyResponse)
async def update_api_key_details(
        key_id: UUID,
        api_key_update: ApiKeyUpdate,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Update a specific API key.

    Args:
        key_id (UUID): The ID of the API key to update.
        api_key_update (ApiKeyUpdate): The API key data to be updated.
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ApiKeyResponse: The updated API key's data.

    Raises:
        HTTPException: If the API key is not found, doesn't belong to the current user, or if there's an error updating it.
    """
    api_key = await get_api_key(db, key_id)
    if not api_key or api_key.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="API key not found")
    try:
        return await update_api_key(db, key_id, api_key_update)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
        key_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a specific API key.

    Args:
        key_id (UUID): The ID of the API key to delete.
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the API key is not found, doesn't belong to the current user, or if there's an error deleting it.
    """
    api_key = await get_api_key(db, key_id)
    if not api_key or api_key.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="API key not found")
    try:
        await delete_api_key(db, key_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
