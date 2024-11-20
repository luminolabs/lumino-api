from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ApiKeyStatus
from app.models.api_key import ApiKey
from app.queries.common import make_naive, now_utc


async def get_api_key_by_prefix(db: AsyncSession, prefix: str) -> Optional[ApiKey]:
    """Get an API key by its prefix."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.prefix == prefix,
        )
    )
    return result.scalar_one_or_none()

async def get_api_key_by_name(db: AsyncSession, user_id: UUID, name: str) -> Optional[ApiKey]:
    """Get an API key by its name for a specific user."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.name == name)
    )
    return result.scalar_one_or_none()

async def list_api_keys(db: AsyncSession, user_id: UUID, offset: int, limit: int) -> List[ApiKey]:
    """List API keys for a specific user with pagination."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id)
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()

async def count_api_keys(db: AsyncSession, user_id: UUID) -> int:
    """Count total API keys for a specific user."""
    result = await db.execute(
        select(func.count()).select_from(ApiKey).where(ApiKey.user_id == user_id)
    )
    return result.scalar_one()

async def mark_expired_keys(db: AsyncSession) -> int:
    """
    Mark expired API keys as EXPIRED.

    Args:
        db: Database session

    Returns:
        Number of keys marked as expired

    Note:
        This is an atomic operation that updates all expired keys at once
    """
    result = await db.execute(
        update(ApiKey)
        .where(
            and_(
                ApiKey.expires_at < make_naive(now_utc()),
                ApiKey.status == ApiKeyStatus.ACTIVE
            )
        )
        .values(
            status=ApiKeyStatus.EXPIRED
        )
        .returning(ApiKey.id)
    )

    updated_keys = result.scalars().all()
    count = len(updated_keys)

    return count
