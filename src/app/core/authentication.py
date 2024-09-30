from datetime import datetime

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config_manager import config
from app.core.constants import UserStatus
from app.core.database import get_db
from app.core.exceptions import InvalidApiKeyError, UnauthorizedError, InvalidUserSessionError, ForbiddenError
from app.core.stripe_client import create_stripe_customer
from app.core.utils import setup_logger
from app.models.api_key import ApiKey
from app.models.user import User

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    Retrieve a user by email.

    Args:
        db (AsyncSession): The database session.
        email (str): The user's email address.
    Returns:
        User | None: The user with the given email address, or None if not found.
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_stripe_customer_id(db: AsyncSession, stripe_customer_id: str) -> User | None:
    """
    Retrieve a user by Stripe customer ID.

    Args:
        db (AsyncSession): The database session.
        stripe_customer_id (str): The user's Stripe customer ID.
    Returns:
        User | None: The user with the given Stripe customer ID, or None if not found.
    """
    result = await db.execute(select(User).where(User.stripe_customer_id == stripe_customer_id))
    return result.scalar_one_or_none()


# This is the scheme we'll use for authenticating users on our API
async def get_api_key(x_api_key: str | None = Header(None)) -> str | None:
    """
    Get the API key from the request header; this is using FastAPI's Header dependency.

    Args:
        x_api_key (str | None): The API key from the request header.
    Returns:
        str: The API key from the request header.
    """
    return x_api_key


async def get_user_from_api_key(db: AsyncSession, api_key: str) -> User:
    """
    Get a user from an API key.

    Args:
        api_key (str): The API key to verify.
        db (AsyncSession): The database session.
    Returns:
        User: The user associated with the API key.
    Raises:
        InvalidApiKeyError: If the API key is invalid or the user can't be found
    """
    # Get the API key from the database
    db_api_key = await db.execute(
        select(ApiKey).options(selectinload(ApiKey.user)).where(
            ApiKey.prefix == api_key[:8],
            ApiKey.status == 'ACTIVE',
            ApiKey.expires_at > datetime.utcnow()
        )
    )
    db_api_key = db_api_key.scalar_one_or_none()
    # Raise an error if the API key is not found
    if not db_api_key:
        raise InvalidApiKeyError(f"API key not found, expired, or revoked: {api_key[:8]}...", logger)
    # Raise an error if the API key can't be verified
    if not db_api_key.verify_key(api_key):
        raise InvalidApiKeyError(f"Can't verify API key: {api_key[:8]}...", logger)
    # Everything checks out, return the user
    logger.info(f"User authenticated via API key: {db_api_key.user.id}, API key: {api_key[:8]}...")
    return db_api_key.user


async def get_session_user(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    """
    Get the user from the session if it exists.

    Args:
        request (Request): The request object.
        db (AsyncSession): The database session.
    Returns:
        User | None: The user from the session, or None if not found.
    """
    user = request.session.get('user')
    if user:
        db_user = await get_user_by_email(db, user['email'])
        if db_user and db_user.status == UserStatus.ACTIVE:
            return db_user


async def get_current_active_user(
        user: User = Depends(get_session_user),
        api_key: str | None = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current active user from either a bearer token or an API key.

    Args:
        user (User | None): The user from the session if it exists.
        api_key (str | None): The API key to verify if it exists.
        db (AsyncSession): The database session.
    Returns:
        UserResponse: The current active user.
    Raises:
        UnauthorizedError: If no API key or bearer token is provided.
        ServerError: If a user or exception is expected, but neither comes back.
    """
    # Check if there is an API key or token provided
    if not api_key and not user:
        raise UnauthorizedError("No x_api_key header or user session found", logger)
    # Check if the API key and associated user are valid
    if api_key:
        user = await get_user_from_api_key(db, api_key)
    # Check if the user session is valid, user exists and is active
    if not user:
        raise InvalidUserSessionError("User session not found, or user not found, or inactive", logger)
    # Create a Stripe customer if they don't have one
    if not user.stripe_customer_id:
        await create_stripe_customer(db, user)
    return user


def admin_required(user: User = Depends(get_current_active_user)):
    if not user.is_admin:
        raise ForbiddenError("Admin access required to perform this action", logger)
    return user