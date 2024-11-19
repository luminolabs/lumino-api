from datetime import timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import ApiKeyStatus
from app.core.cryptography import generate_api_key
from app.core.exceptions import (
    ApiKeyAlreadyExistsError,
    ApiKeyNotFoundError,
)
from app.core.utils import setup_logger
from app.models.api_key import ApiKey
from app.queries import api_keys as api_key_queries
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse, ApiKeyWithSecretResponse
from app.schemas.common import Pagination

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def create_api_key(db: AsyncSession, user_id: UUID, api_key: ApiKeyCreate) -> ApiKeyWithSecretResponse:
    """Create a new API key for a user."""
    # Check if an API key with the same name already exists for this user
    existing_key = await api_key_queries.get_api_key_by_name(db, user_id, api_key.name)
    if existing_key:
        raise ApiKeyAlreadyExistsError(f"An API key with the name {api_key.name} "
                                       f"already exists for user {user_id}", logger)

    # Generate a new API key
    key, key_hash = generate_api_key()
    key_prefix = key[:8]

    # Ensure the expires_at field is stored as timezone-naive UTC datetime
    expires_at = api_key.expires_at.astimezone(timezone.utc)
    expires_at = expires_at.replace(tzinfo=None)

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
    await db.refresh(db_api_key)

    # Restore the timezone to the expires_at field
    db_api_key.expires_at = expires_at.replace(tzinfo=timezone.utc)

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
    """Get all API keys for a user with pagination."""
    offset = (page - 1) * items_per_page

    # Get total count and paginated results
    total_count = await api_key_queries.count_api_keys(db, user_id)
    api_keys = await api_key_queries.list_api_keys(db, user_id, offset, items_per_page)

    # Calculate pagination
    total_pages = (total_count + items_per_page - 1) // items_per_page
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
    )

    # Create response objects
    api_key_responses = [ApiKeyResponse.from_orm(key) for key in api_keys]

    logger.info(f"Retrieved API keys for user: {user_id}, page: {page}")
    return api_key_responses, pagination


async def get_api_key(db: AsyncSession, user_id: UUID, key_name: str) -> ApiKeyResponse:
    """Get a specific API key."""
    api_key = await api_key_queries.get_api_key_by_name(db, user_id, key_name)
    if not api_key:
        raise ApiKeyNotFoundError(f"API key not found: {key_name} for user: {user_id}", logger)

    logger.info(f"Retrieved API key: {key_name} for user: {user_id}")
    return ApiKeyResponse.from_orm(api_key)


async def update_api_key(db: AsyncSession, user_id: UUID, key_name: str, api_key_update: ApiKeyUpdate) -> ApiKeyResponse:
    """Update an API key."""
    db_api_key = await api_key_queries.get_api_key_by_name(db, user_id, key_name)
    if not db_api_key:
        raise ApiKeyNotFoundError(f"API key not found: {key_name} for user: {user_id}", logger)

    # Ensure the expires_at field is stored as timezone-naive UTC datetime
    expires_at = api_key_update.expires_at
    if expires_at:
        expires_at = expires_at.astimezone(timezone.utc)
        expires_at = expires_at.replace(tzinfo=None)
        api_key_update.expires_at = expires_at

    # Update the API key fields
    update_data = api_key_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_api_key, field, value)

    await db.commit()
    await db.refresh(db_api_key)

    # Restore the timezone to the expires_at field
    db_api_key.expires_at = db_api_key.expires_at.replace(tzinfo=timezone.utc)

    logger.info(f"Updated API key: {key_name} for user: {user_id}")
    return ApiKeyResponse.from_orm(db_api_key)


async def revoke_api_key(db: AsyncSession, user_id: UUID, key_name: str) -> ApiKeyResponse:
    """Revoke an API key."""
    db_api_key = await api_key_queries.get_api_key_by_name(db, user_id, key_name)
    if not db_api_key:
        raise ApiKeyNotFoundError(f"API key not found: {key_name} for user: {user_id}", logger)

    db_api_key.status = ApiKeyStatus.REVOKED
    await db.commit()
    await db.refresh(db_api_key)

    logger.info(f"Revoked API key: {key_name} for user: {user_id}")
    return ApiKeyResponse.from_orm(db_api_key)
