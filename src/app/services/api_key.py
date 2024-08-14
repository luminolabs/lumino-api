import math
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.constants import ApiKeyStatus
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse, ApiKeyWithSecret
from app.core.security import generate_api_key, verify_api_key_hash
from app.schemas.common import Pagination
from app.utils import setup_logger
from app.core.exceptions import (
    ApiKeyCreationError,
    ApiKeyNotFoundError,
    ApiKeyUpdateError,
    ApiKeyRevocationError
)

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def create_api_key(db: AsyncSession, user_id: UUID, api_key: ApiKeyCreate) -> ApiKeyWithSecret:
    """
    Create a new API key for a user.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user creating the API key.
        api_key (ApiKeyCreate): The API key creation data.

    Returns:
        ApiKeyWithSecret: The newly created API key, including the secret.

    Raises:
        ApiKeyCreationError: If there's an error creating the API key.
    """
    try:
        # Check if an API key with the same name already exists for this user
        existing_key = await db.execute(
            select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.name == api_key.name)
        )
        if existing_key.scalar_one_or_none():
            logger.warning(f"Attempt to create duplicate API key name '{api_key.name}' for user {user_id}")
            raise ApiKeyCreationError(f"An API key with the name '{api_key.name}' already exists")

        key, hashed_key = generate_api_key()
        prefix = key[:8]

        # Handle expires_at to ensure timezone consistency
        expires_at = api_key.expires_at
        if expires_at is not None:
            # Ensure the datetime is timezone-aware and convert to UTC
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at = expires_at.astimezone(timezone.utc)
            # Store as timezone-naive UTC in the database
            expires_at = expires_at.replace(tzinfo=None)

        db_api_key = ApiKey(
            user_id=user_id,
            name=api_key.name,
            expires_at=expires_at,
            prefix=prefix,
            hashed_key=hashed_key,
            status=ApiKeyStatus.ACTIVE,
        )
        db.add(db_api_key)
        await db.commit()
        await db.refresh(db_api_key)

        logger.info(f"Created new API key for user: {user_id}")
        return ApiKeyWithSecret(
            **ApiKeyResponse.from_orm(db_api_key).dict(),
            secret=key
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error while creating API key for user {user_id}: {str(e)}")
        await db.rollback()
        raise ApiKeyCreationError("Failed to create API key due to a database error")


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
    try:
        # Count total items
        total_count = await db.scalar(
            select(func.count()).select_from(ApiKey).where(ApiKey.user_id == user_id)
        )

        # Calculate pagination
        total_pages = math.ceil(total_count / items_per_page)
        offset = (page - 1) * items_per_page

        # Fetch items
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .offset(offset)
            .limit(items_per_page)
        )
        api_keys = [ApiKeyResponse.from_orm(key) for key in result.scalars().all()]

        # Create pagination object
        pagination = Pagination(
            total_pages=total_pages,
            current_page=page,
            items_per_page=items_per_page,
            next_page=page + 1 if page < total_pages else None,
            previous_page=page - 1 if page > 1 else None
        )

        logger.info(f"Retrieved API keys for user: {user_id}, page: {page}")
        return api_keys, pagination
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching API keys for user {user_id}: {str(e)}")
        raise ApiKeyNotFoundError("Failed to retrieve API keys due to a database error")


async def get_api_key(db: AsyncSession, user_id: UUID, key_name: str) -> ApiKeyResponse | None:
    """
    Get a specific API key.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        key_name (str): The name of the API key.

    Returns:
        ApiKeyResponse | None: The API key if found, None otherwise.

    Raises:
        ApiKeyNotFoundError: If the API key is not found.
    """
    try:
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id, ApiKey.name == key_name)
        )
        api_key = result.scalar_one_or_none()
        if api_key:
            logger.info(f"Retrieved API key: {key_name} for user: {user_id}")
            return ApiKeyResponse.from_orm(api_key)
        logger.warning(f"API key not found: {key_name} for user: {user_id}")
        return None
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching API key {key_name} for user {user_id}: {str(e)}")
        raise ApiKeyNotFoundError("Failed to retrieve API key due to a database error")


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
        ApiKeyUpdateError: If there's an error updating the API key.
    """
    try:
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id, ApiKey.name == key_name)
        )
        db_api_key = result.scalar_one_or_none()
        if not db_api_key:
            logger.warning(f"API key not found for update: {key_name} for user: {user_id}")
            raise ApiKeyNotFoundError("API key not found")

        update_data = api_key_update.dict(exclude_unset=True)

        # Handle expires_at separately to ensure timezone consistency
        if 'expires_at' in update_data:
            expires_at = update_data['expires_at']
            if expires_at is not None:
                # Ensure the datetime is timezone-aware and convert to UTC
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                else:
                    expires_at = expires_at.astimezone(timezone.utc)
                # Store as timezone-naive UTC in the database
                update_data['expires_at'] = expires_at.replace(tzinfo=None)

        for field, value in update_data.items():
            setattr(db_api_key, field, value)

        await db.commit()
        await db.refresh(db_api_key)
        logger.info(f"Updated API key: {key_name} for user: {user_id}")
        return ApiKeyResponse.from_orm(db_api_key)
    except SQLAlchemyError as e:
        logger.error(f"Database error while updating API key {key_name} for user {user_id}: {str(e)}")
        await db.rollback()
        raise ApiKeyUpdateError("Failed to update API key due to a database error")


async def revoke_api_key(db: AsyncSession, user_id: UUID, key_name: str) -> ApiKeyResponse:
    """
    Revoke an API key by marking it as revoked.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        key_name (str): The name of the API key to revoke.

    Raises:
        ApiKeyNotFoundError: If the API key is not found.
        ApiKeyRevocationError: If there's an error revoking the API key.
    """
    try:
        result = await db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id, ApiKey.name == key_name)
        )
        db_api_key = result.scalar_one_or_none()
        if not db_api_key:
            logger.warning(f"API key not found for revocation: {key_name} for user: {user_id}")
            raise ApiKeyNotFoundError("API key not found")

        db_api_key.status = ApiKeyStatus.REVOKED
        # Store as timezone-naive UTC datetime
        db_api_key.expires_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        await db.refresh(db_api_key)
        logger.info(f"Revoked API key: {key_name} for user: {user_id}")
        return ApiKeyResponse.from_orm(db_api_key)
    except SQLAlchemyError as e:
        logger.error(f"Database error while revoking API key {key_name} for user {user_id}: {str(e)}")
        await db.rollback()
        raise ApiKeyRevocationError("Failed to revoke API key due to a database error")


async def verify_api_key(db: AsyncSession, api_key: str) -> UUID | None:
    """
    Verify an API key and return the associated user ID.

    Args:
        db (AsyncSession): The database session.
        api_key (str): The API key to verify.

    Returns:
        UUID | None: The user ID associated with the API key if valid, None otherwise.
    """
    try:
        prefix = api_key[:8]
        result = await db.execute(select(ApiKey).where(ApiKey.prefix == prefix))
        db_api_key = result.scalar_one_or_none()

        if db_api_key and db_api_key.status == ApiKeyStatus.ACTIVE and verify_api_key_hash(api_key, db_api_key.hashed_key):
            if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
                logger.warning(f"Expired API key used: {prefix}")
                return None
            db_api_key.last_used_at = datetime.utcnow()
            await db.commit()
            logger.info(f"Valid API key used: {prefix}")
            return db_api_key.user_id

        logger.warning(f"Invalid API key used: {prefix}")
        return None
    except SQLAlchemyError as e:
        logger.error(f"Database error while verifying API key: {str(e)}")
        return None