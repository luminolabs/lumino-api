from typing import Dict, Union, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.authentication import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyUpdate, ApiKeyWithSecretResponse
from app.schemas.common import Pagination
from app.services.api_key import (
    create_api_key,
    get_api_keys,
    get_api_key,
    update_api_key,
    revoke_api_key,
)
from app.core.utils import setup_logger

# Set up API router
router = APIRouter(tags=["API Keys"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.post("/api-keys", response_model=ApiKeyWithSecretResponse, status_code=status.HTTP_201_CREATED)
async def create_new_api_key(
        api_key: ApiKeyCreate,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyWithSecretResponse:
    """
    Create a new API key for the current user.

    Args:
        api_key (ApiKeyCreate): The API key creation data.
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ApiKeyResponse: The newly created API key.
    """
    new_api_key = await create_api_key(db, current_user.id, api_key)
    return new_api_key


@router.get("/api-keys", response_model=Dict[str, Union[List[ApiKeyResponse], Pagination]])
async def list_api_keys(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[ApiKeyResponse], Pagination]]:
    """
    List all API keys for the current user.

    Args:
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        Dict[str, Union[List[ApiKeyResponse], Pagination]]: A dictionary containing the list of API keys and pagination info.
    """
    api_keys, pagination = await get_api_keys(db, current_user.id, page, items_per_page)
    return {
        "data": api_keys,
        "pagination": pagination
    }


@router.get("/api-keys/{key_name}", response_model=ApiKeyResponse)
async def get_api_key_details(
        key_name: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Get details of a specific API key.

    Args:
        key_name (str): The name of the API key.
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ApiKeyResponse: The details of the requested API key.
    """
    api_key = await get_api_key(db, current_user.id, key_name)
    return api_key


@router.patch("/api-keys/{key_name}", response_model=ApiKeyResponse)
async def update_api_key_details(
        key_name: str,
        api_key_update: ApiKeyUpdate,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Update a specific API key.

    Args:
        key_name (str): The name of the API key to update.
        api_key_update (ApiKeyUpdate): The update data for the API key.
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ApiKeyResponse: The updated API key.
    """
    updated_key = await update_api_key(db, current_user.id, key_name, api_key_update)
    return updated_key


@router.delete("/api-keys/{key_name}", response_model=ApiKeyResponse)
async def revoke_api_key_route(
        key_name: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Revoke a specific API key.

    Args:
        key_name (str): The name of the API key to revoke.
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ApiKeyResponse: The revoked API key.
    """
    revoked_key = await revoke_api_key(db, current_user.id, key_name)
    return revoked_key