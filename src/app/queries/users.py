from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """Get a user by ID."""
    return await db.get(User, user_id)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get a user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_stripe_customer_id(db: AsyncSession, stripe_customer_id: str) -> Optional[User]:
    """Get a user by Stripe customer ID."""
    result = await db.execute(select(User).where(User.stripe_customer_id == stripe_customer_id))
    return result.scalar_one_or_none()
