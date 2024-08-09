from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.api_key import ApiKey
from app.schemas.api_key import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse, ApiKeyWithSecret
from app.core.security import generate_api_key, verify_api_key_hash


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
        status="active"
    )
    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)

    return ApiKeyWithSecret(
        **ApiKeyResponse.from_orm(db_api_key).dict(),
        secret=key
    )


async def get_api_keys(db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100) -> list[ApiKeyResponse]:
    """Get all API keys for a user."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return [ApiKeyResponse.from_orm(api_key) for api_key in result.scalars().all()]


async def get_api_key(db: AsyncSession, api_key_id: UUID) -> ApiKeyResponse | None:
    """Get a specific API key."""
    api_key = await db.get(ApiKey, api_key_id)
    if api_key:
        return ApiKeyResponse.from_orm(api_key)
    return None


async def update_api_key(db: AsyncSession, api_key_id: UUID, api_key_update: ApiKeyUpdate) -> ApiKeyResponse:
    """Update an API key."""
    db_api_key = await db.get(ApiKey, api_key_id)
    if not db_api_key:
        raise ValueError("API key not found")

    update_data = api_key_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_api_key, field, value)

    await db.commit()
    await db.refresh(db_api_key)
    return ApiKeyResponse.from_orm(db_api_key)


async def delete_api_key(db: AsyncSession, api_key_id: UUID) -> None:
    """Delete an API key."""
    db_api_key = await db.get(ApiKey, api_key_id)
    if not db_api_key:
        raise ValueError("API key not found")

    await db.delete(db_api_key)
    await db.commit()


async def verify_api_key(db: AsyncSession, api_key: str) -> UUID | None:
    """Verify an API key and return the associated user ID."""
    prefix = api_key[:8]
    result = await db.execute(select(ApiKey).where(ApiKey.prefix == prefix))
    db_api_key = result.scalar_one_or_none()

    if db_api_key and db_api_key.status == "active" and verify_api_key_hash(api_key, db_api_key.hashed_key):
        if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
            return None
        db_api_key.last_used_at = datetime.utcnow()
        await db.commit()
        return db_api_key.user_id

    return None