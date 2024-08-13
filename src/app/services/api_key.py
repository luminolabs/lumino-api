import math
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ApiKeyStatus
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse, ApiKeyWithSecret
from app.core.security import generate_api_key, verify_api_key_hash
from app.schemas.common import Pagination


async def create_api_key(db: AsyncSession, user_id: UUID, api_key: ApiKeyCreate) -> ApiKeyWithSecret:
    """Create a new API key."""
    key, hashed_key = generate_api_key()
    prefix = key[:8]

    db_api_key = ApiKey(
        user_id=user_id,
        name=api_key.name,
        expires_at=api_key.expires_at,
        prefix=prefix,
        hashed_key=hashed_key,
        status=ApiKeyStatus.ACTIVE,
    )
    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)

    return ApiKeyWithSecret(
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

    return api_keys, pagination


async def get_api_key(db: AsyncSession, user_id: UUID, key_name: str) -> ApiKeyResponse | None:
    """Get a specific API key."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id, ApiKey.name == key_name)
    )
    api_key = result.scalar_one_or_none()
    if api_key:
        return ApiKeyResponse.from_orm(api_key)
    return None


async def update_api_key(db: AsyncSession, user_id: UUID, key_name: str, api_key_update: ApiKeyUpdate) -> ApiKeyResponse:
    """Update an API key."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id, ApiKey.name == key_name)
    )
    db_api_key = result.scalar_one_or_none()
    if not db_api_key:
        raise ValueError("API key not found")

    update_data = api_key_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_api_key, field, value)

    await db.commit()
    await db.refresh(db_api_key)
    return ApiKeyResponse.from_orm(db_api_key)


async def delete_api_key(db: AsyncSession, user_id: UUID, key_name: str) -> None:
    """Delete an API key."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id, ApiKey.name == key_name)
    )
    db_api_key = result.scalar_one_or_none()
    if not db_api_key:
        raise ValueError("API key not found")

    await db.delete(db_api_key)
    await db.commit()


async def verify_api_key(db: AsyncSession, api_key: str) -> UUID | None:
    """Verify an API key and return the associated user ID."""
    prefix = api_key[:8]
    result = await db.execute(select(ApiKey).where(ApiKey.prefix == prefix))
    db_api_key = result.scalar_one_or_none()

    if db_api_key and db_api_key.status == ApiKeyStatus.ACTIVE and verify_api_key_hash(api_key, db_api_key.hashed_key):
        if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
            return None
        db_api_key.last_used_at = datetime.utcnow()
        await db.commit()
        return db_api_key.user_id

    return None
