from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UserStatus
from app.core.database import get_db
from app.core.exceptions import (
    InvalidApiKeyError,
    UnauthorizedError,
    InvalidUserSessionError,
    ForbiddenError
)
from app.core.stripe_client import create_stripe_customer
from app.core.utils import setup_logger
from app.models.user import User
from app.queries import api_keys as api_key_queries
from app.queries import users as user_queries

logger = setup_logger(__name__)

async def get_api_key(x_api_key: str | None = Header(None)) -> str | None:
    """Get API key from request header."""
    return x_api_key

async def get_user_from_api_key(db: AsyncSession, api_key: str) -> User:
    """
    Get user associated with an API key.

    Args:
        api_key: The API key to verify
        db: Database session

    Returns:
        Associated user

    Raises:
        InvalidApiKeyError: If API key is invalid
    """
    # Get API key from database
    db_api_key = await api_key_queries.get_api_key_by_prefix(db, api_key[:8])

    if not db_api_key:
        raise InvalidApiKeyError(
            f"API key not found, expired, or revoked: {api_key[:8]}...",
            logger
        )

    if not db_api_key.verify_key(api_key):
        raise InvalidApiKeyError(
            f"Can't verify API key: {api_key[:8]}...",
            logger
        )

    user = await user_queries.get_user_by_id(db, db_api_key.user_id)
    logger.info(
        f"User authenticated via API key: {user}, "
        f"API key: {api_key[:8]}..."
    )
    return user

async def get_session_user(
        request: Request,
        db: AsyncSession = Depends(get_db)
) -> User | None:
    """Get user from session."""
    user = request.session.get('user')
    if user:
        db_user = await user_queries.get_user_by_email(db, user['email'])
        if db_user and db_user.status == UserStatus.ACTIVE:
            return db_user
    return None

async def get_current_active_user(
        user: User = Depends(get_session_user),
        api_key: str | None = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current active user from session or API key.

    Args:
        user: User from session
        api_key: API key from header
        db: Database session

    Returns:
        Current active user

    Raises:
        UnauthorizedError: If no valid authentication
        InvalidUserSessionError: If user session invalid
    """
    if not api_key and not user:
        raise UnauthorizedError(
            "No x_api_key header or user session found",
            logger
        )

    if api_key:
        user = await get_user_from_api_key(db, api_key)

    if not user:
        raise InvalidUserSessionError(
            "User session not found, or user not found, or inactive",
            logger
        )

    # Ensure user has Stripe customer ID
    if not user.stripe_customer_id:
        await create_stripe_customer(db, user)

    return user

def admin_required(user: User = Depends(get_current_active_user)) -> User:
    """Verify user is admin."""
    if not user.is_admin:
        raise ForbiddenError(
            "Admin access required to perform this action",
            logger
        )
    return user
