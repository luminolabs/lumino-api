from uuid import UUID
from datetime import timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import ApiKeyStatus
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse, ApiKeyWithSecretResponse
from app.core.cryptography import generate_api_key
from app.schemas.common import Pagination
from app.core.utils import setup_logger, paginate_query
from app.core.exceptions import (
    ApiKeyAlreadyExistsError,
    ApiKeyNotFoundError,
)

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def create_api_key(db: AsyncSession, user_id: UUID, api_key: ApiKeyCreate) -> ApiKeyWithSecretResponse:
    """
    Create a new API key for a user.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user creating the API key.
        api_key (ApiKeyCreate): The API key creation data.

    Returns:
        ApiKeyWithSecretResponse: The newly created API key, including the secret.

    Raises:
        ApiKeyCreationError: If there's an error creating the API key.
    """
    # Check if an API key with the same name already exists for this user
    existing_key = (await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.name == api_key.name)
    )).scalar_one_or_none()
    if existing_key:
        raise ApiKeyAlreadyExistsError(f"An API key with the name {api_key.name} "
                                  f"already exists for user {user_id}", logger)

    # Generate a new API key
    key, key_hash = generate_api_key()
    key_prefix = key[:8]

    # Ensure the expires_at field is stored as timezone-naive UTC datetime
    expires_at = api_key.expires_at
    expires_at = expires_at.astimezone(timezone.utc)
    expires_at = expires_at.replace(tzinfo=None)  # TODO: We get a db error here if we don't do this; figure out why

    # Store the API key in the database
    db_api_key = ApiKey(
        user_id=user_id,
        name=api_key.name,
        expires_at=expires_at,
        prefix=key_prefix,
        key_hash=key_hash,
        status=ApiKeyStatus.ACTIVE,
    )
    db.add(db_api_key)
    await db.commit()

    # Restore the timezone to the expires_at field as UTC timezone-aware datetime
    expires_at = expires_at.replace(tzinfo=timezone.utc)
    db_api_key.expires_at = expires_at

    # Return the API key with the full secret
    # We only return the generated secret once, so the user can store it
    logger.info(f"Created new API key for user: {user_id}, prefix: {key_prefix}")
    return ApiKeyWithSecretResponse(
        **ApiKeyResponse.from_orm(db_api_key).dict(),
        secret=key
    )


async def get_api_keys(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[ApiKeyResponse], Pagination]:
    """
    Get all API keys for a user with pagination.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        tuple[list[ApiKeyResponse], Pagination]: A tuple containing the list of API keys and pagination info.
    """
    # Construct the query
    query = select(ApiKey).where(ApiKey.user_id == user_id)
    # Paginate the query
    api_keys, pagination = await paginate_query(db, query, page, items_per_page)
    # Create response objects
    api_key_responses = [ApiKeyResponse.from_orm(key) for key in api_keys]
    # Log and return objects
    logger.info(f"Retrieved API keys for user: {user_id}, page: {page}")
    return api_key_responses, pagination


async def get_api_key(db: AsyncSession, user_id: UUID, key_name: str) -> ApiKeyResponse:
    """
    Get a specific API key.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        key_name (str): The name of the API key.

    Returns:
        ApiKeyResponse: The API key if found, None otherwise.

    Raises:
        ApiKeyNotFoundError: If the API key is not found.
    """
    # Get the API key from the database
    api_key = (await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id, ApiKey.name == key_name)
    )).scalar_one_or_none()

    # Raise an error if the API key is not found
    if not api_key:
        raise ApiKeyNotFoundError(f"API key not found: {key_name} for user: {user_id}", logger)

    # Log and return the API key
    logger.info(f"Retrieved API key: {key_name} for user: {user_id}")
    return ApiKeyResponse.from_orm(api_key)


async def update_api_key(db: AsyncSession, user_id: UUID, key_name: str, api_key_update: ApiKeyUpdate) -> ApiKeyResponse:
    """
    Update an API key.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        key_name (str): The name of the API key to update.
        api_key_update (ApiKeyUpdate): The update data for the API key.

    Returns:
        ApiKeyResponse: The updated API key.

    Raises:
        ApiKeyNotFoundError: If the API key is not found.
    """
    # Get the API key from the database
    db_api_key = (await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id, ApiKey.name == key_name)
    )).scalar_one_or_none()

    # Raise an error if the API key is not found
    if not db_api_key:
        raise ApiKeyNotFoundError(f"API key not found: {key_name} for user: {user_id}", logger)

    # Ensure the expires_at field is stored as timezone-naive UTC datetime
    expires_at = api_key_update.expires_at
    expires_at = expires_at.astimezone(timezone.utc)
    expires_at = expires_at.replace(tzinfo=None)  # TODO: We get a db error here if we don't do this; figure out why
    api_key_update.expires_at = expires_at

    # Update the API key fields with the new data from the request
    update_data = api_key_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_api_key, field, value)

    # Store the updated API key in the database
    await db.commit()
    
    # Restore the timezone to the expires_at field as UTC timezone-aware datetime
    db_api_key.expires_at = db_api_key.expires_at.replace(tzinfo=timezone.utc)
    
    # Log and return the updated API key
    logger.info(f"Updated API key: {key_name} for user: {user_id}")
    return ApiKeyResponse.from_orm(db_api_key)


async def revoke_api_key(db: AsyncSession, user_id: UUID, key_name: str) -> ApiKeyResponse:
    """
    Revoke an API key by marking it as revoked.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        key_name (str): The name of the API key to revoke.

    Raises:
        ApiKeyNotFoundError: If the API key is not found.
    """
    # Get the API key from the database
    db_api_key = (await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id, ApiKey.name == key_name)
    )).scalar_one_or_none()
    # Raise an error if the API key is not found
    if not db_api_key:
        raise ApiKeyNotFoundError(f"API key not found: {key_name} for user: {user_id}", logger)

    # Mark the API key as revoked
    db_api_key.status = ApiKeyStatus.REVOKED
    
    # Store the updated API key in the database
    await db.commit()
    
    # Log and return the revoked API key
    logger.info(f"Revoked API key: {key_name} for user: {user_id}")
    return ApiKeyResponse.from_orm(db_api_key)
