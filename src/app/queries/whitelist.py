from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.whitelist import Whitelist


async def get_whitelist_by_user_id(db: AsyncSession, user_id: UUID) -> Optional[Whitelist]:
    """Get a whitelist request by user ID."""
    result = await db.execute(
        select(Whitelist).where(Whitelist.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def is_user_whitelisted(db: AsyncSession, user_id: UUID) -> bool:
    """Check if a user is whitelisted."""
    whitelist = await get_whitelist_by_user_id(db, user_id)
    return whitelist is not None and whitelist.is_whitelisted


async def has_user_signed_nda(db: AsyncSession, user_id: UUID) -> bool:
    """Check if a user has signed the NDA."""
    whitelist = await get_whitelist_by_user_id(db, user_id)
    return whitelist is not None and whitelist.has_signed_nda