from typing import List, Union, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyUpdate
from app.schemas.common import Pagination
from app.services.api_key import (
    create_api_key,
    get_api_keys,
    get_api_key,
    update_api_key,
    delete_api_key,
)
from app.core.authentication import get_current_active_user
from app.schemas.user import UserResponse

router = APIRouter(tags=["API Keys"])


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_new_api_key(
        api_key: ApiKeyCreate,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Create a new API key for the current user.
    """
    try:
        return await create_api_key(db, current_user.id, api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api-keys", response_model=Dict[str, Union[List[ApiKeyResponse], Pagination]])
async def list_api_keys(
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> dict:
    """
    List all API keys for the current user.
    """
    api_keys, pagination = await get_api_keys(db, current_user.id, page, items_per_page)
    return {
        "data": api_keys,
        "pagination": pagination
    }


@router.get("/api-keys/{key_name}", response_model=ApiKeyResponse)
async def get_api_key_details(
        key_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Get details of a specific API key.
    """
    api_key = await get_api_key(db, current_user.id, key_name)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    return api_key


@router.patch("/api-keys/{key_name}", response_model=ApiKeyResponse)
async def update_api_key_details(
        key_name: str,
        api_key_update: ApiKeyUpdate,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Update a specific API key.
    """
    try:
        return await update_api_key(db, current_user.id, key_name, api_key_update)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/api-keys/{key_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
        key_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a specific API key.
    """
    try:
        await delete_api_key(db, current_user.id, key_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))