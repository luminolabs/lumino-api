from typing import Dict, Union, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import get_current_active_user
from app.core.config_manager import config
from app.core.database import get_db
from app.core.utils import setup_logger
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
    """Create a new API key."""
    return await create_api_key(db, current_user.id, api_key)


@router.get("/api-keys", response_model=Dict[str, Union[List[ApiKeyResponse], Pagination]])
async def list_api_keys(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[ApiKeyResponse], Pagination]]:
    """List all API keys for the current user."""
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
    """Get details of a specific API key."""
    return await get_api_key(db, current_user.id, key_name)


@router.patch("/api-keys/{key_name}", response_model=ApiKeyResponse)
async def update_api_key_details(
        key_name: str,
        api_key_update: ApiKeyUpdate,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """Update a specific API key."""
    return await update_api_key(db, current_user.id, key_name, api_key_update)


@router.delete("/api-keys/{key_name}", response_model=ApiKeyResponse)
async def revoke_api_key_route(
        key_name: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """Revoke a specific API key."""
    return await revoke_api_key(db, current_user.id, key_name)
