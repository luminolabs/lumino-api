from typing import Dict, Union, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.core.authentication import get_current_active_user
from app.core.exceptions import (
    BadRequestError,
    NotFoundError,
    ApiKeyCreationError,
    ApiKeyNotFoundError,
    ApiKeyUpdateError,
    ApiKeyRevocationError
)
from app.database import get_db
from app.schemas.api_key import ApiKeyCreate, ApiKeyResponse, ApiKeyUpdate
from app.schemas.common import Pagination
from app.schemas.user import UserResponse
from app.services.api_key import (
    create_api_key,
    get_api_keys,
    get_api_key,
    update_api_key,
    revoke_api_key,
)
from app.utils import setup_logger

router = APIRouter(tags=["API Keys"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_new_api_key(
        api_key: ApiKeyCreate,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Create a new API key for the current user.

    Args:
        api_key (ApiKeyCreate): The API key creation data.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ApiKeyResponse: The newly created API key.

    Raises:
        ApiKeyCreationError: If there's an error creating the API key.
    """
    try:
        logger.info(f"Creating new API key for user: {current_user.id}")
        new_api_key = await create_api_key(db, current_user.id, api_key)
        logger.info(f"Successfully created API key for user: {current_user.id}")
        return new_api_key
    except ApiKeyCreationError as e:
        logger.error(f"Error creating API key for user {current_user.id}: {str(e)}")
        raise BadRequestError(e.detail)


@router.get("/api-keys", response_model=Dict[str, Union[List[ApiKeyResponse], Pagination]])
async def list_api_keys(
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[ApiKeyResponse], Pagination]]:
    """
    List all API keys for the current user.

    Args:
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        Dict[str, Union[List[ApiKeyResponse], Pagination]]: A dictionary containing the list of API keys and pagination info.
    """
    logger.info(f"Fetching API keys for user: {current_user.id}")
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

    Args:
        key_name (str): The name of the API key.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ApiKeyResponse: The details of the requested API key.

    Raises:
        ApiKeyNotFoundError: If the API key is not found.
    """
    logger.info(f"Fetching API key details for user: {current_user.id}, key name: {key_name}")
    api_key = await get_api_key(db, current_user.id, key_name)
    if not api_key:
        logger.warning(f"API key not found for user: {current_user.id}, key name: {key_name}")
        raise ApiKeyNotFoundError("API key not found")
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

    Args:
        key_name (str): The name of the API key to update.
        api_key_update (ApiKeyUpdate): The update data for the API key.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ApiKeyResponse: The updated API key.

    Raises:
        ApiKeyNotFoundError: If the API key is not found.
        ApiKeyUpdateError: If there's an error updating the API key.
    """
    try:
        logger.info(f"Updating API key for user: {current_user.id}, key name: {key_name}")
        updated_key = await update_api_key(db, current_user.id, key_name, api_key_update)
        logger.info(f"Successfully updated API key for user: {current_user.id}, key name: {key_name}")
        return updated_key
    except ApiKeyNotFoundError as e:
        logger.error(f"API key not found for user {current_user.id}, key name {key_name}: {str(e)}")
        raise NotFoundError(e.detail)
    except ApiKeyUpdateError as e:
        logger.error(f"Error updating API key for user {current_user.id}, key name {key_name}: {str(e)}")
        raise BadRequestError(e.detail)


@router.delete("/api-keys/{key_name}", response_model=ApiKeyResponse)
async def revoke_api_key_route(
        key_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """
    Revoke a specific API key.

    Args:
        key_name (str): The name of the API key to revoke.
        current_user (UUID): The UUID of the current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ApiKeyResponse: The revoked API key.

    Raises:
        ApiKeyNotFoundError: If the API key is not found.
        ApiKeyRevocationError: If there's an error revoking the API key.
    """
    try:
        logger.info(f"Revoking API key for user: {current_user.id}, key name: {key_name}")
        revoked_key = await revoke_api_key(db, current_user.id, key_name)
        logger.info(f"Successfully revoked API key for user: {current_user.id}, key name: {key_name}")
        return revoked_key
    except ApiKeyNotFoundError as e:
        logger.error(f"API key not found for user {current_user.id}, key name {key_name}: {str(e)}")
        raise NotFoundError(e.detail)
    except ApiKeyRevocationError as e:
        logger.error(f"Error revoking API key for user {current_user.id}, key name {key_name}: {str(e)}")
        raise BadRequestError(e.detail)