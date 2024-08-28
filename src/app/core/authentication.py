from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import UserStatus
from app.core.exceptions import InvalidApiKeyError, InvalidBearerTokenError, UnauthorizedError, ServerError
from app.core.cryptography import decode_bearer_token, create_bearer_token
from app.core.database import get_db
from app.models.api_key import ApiKey
from app.models.blacklisted_token import BlacklistedToken
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.user import logger, get_user_by_email
from app.core.utils import setup_logger

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)

# This is the scheme we'll use for authenticating users on our web UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


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
    db_api_key = (await db.execute(
        select(ApiKey).where(
            ApiKey.prefix == api_key[:8],
            ApiKey.status == 'ACTIVE',
            ApiKey.expires_at > datetime.utcnow()
        )
    )).scalar_one_or_none()
    # Raise an error if the API key is not found
    if not db_api_key:
        raise InvalidApiKeyError(f"API key not found or expired: {api_key[:8]}...", logger)
    # Raise an error if the API key can't be verified
    if not db_api_key.verify_key(api_key):
        raise InvalidApiKeyError(f"Can't verify API key: {api_key[:8]}...", logger)
    # Everything checks out, return the user
    logger.info(f"User authenticated via API key: {db_api_key.user.id}, API key: {api_key[:8]}...")
    return db_api_key.user


async def get_user_from_bearer_token(token: str, db: AsyncSession) -> User:
    """
    Get a user from a bearer token.

    Args:
        token (str): The bearer token to decode and verify.
        db (AsyncSession): The database session.
    Returns:
        User: The user associated with the bearer token.
    Raises:
        InvalidTokenError: If the bearer token is invalid or the user can't be found.
    """
    # Decode the token
    payload = decode_bearer_token(token)
    # Check if the token is logged out
    if await is_bearer_token_logged_out(db, token):
        raise InvalidBearerTokenError(f"Bearer token is logged out: {token[:8]}...", logger)
    # Get the user id from the token payload
    user_id: str = payload.get("sub")
    if user_id is None:
        raise InvalidBearerTokenError(f"Bearer token does not contain user ID: {token[:8]}...", logger)
    # Get the user from the database
    db_user = await db.get(User, UUID(user_id))
    if not db_user:
        raise InvalidBearerTokenError(f"User not found for bearer token: {token[:8]}...", logger)
    # Everything checks out, return the user
    logger.info(f"User authenticated via bearer token: {db_user.id}, token: {token[:8]}...")
    return db_user


async def get_current_active_user(
        token: str | None = Depends(oauth2_scheme),
        api_key: str | None = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current active user from either a bearer token or an API key.

    Args:
        token (str | None): The bearer token to decode and verify.
        api_key (str | None): The API key to verify.
        db (AsyncSession): The database session.
    Returns:
        UserResponse: The current active user.
    Raises:
        UnauthorizedError: If no API key or bearer token is provided.
        ServerError: If a user or exception is expected, but neither comes back.
    """
    # Check if there is an API key or token provided
    if not api_key and not token:
        raise UnauthorizedError("No API key or bearer token provided", logger)
    # Check if the API key and associated user are valid
    if api_key:
        db_user = await get_user_from_api_key(db, api_key)
        if db_user and db_user.status == UserStatus.ACTIVE:
            return db_user
    # Check if the bearer token and associated user are valid
    if token:
        db_user = await get_user_from_bearer_token(token, db)
        if db_user and db_user.status == UserStatus.ACTIVE:
            return db_user
    # We shouldn't get here, but if we do, raise a server error
    raise ServerError("User or exception expected, but got neither", logger)


async def logout_bearer_token(token: str, db: AsyncSession):
    """
    Blacklist a bearer token.

    Args:
        token (str): The bearer token to blacklist.
        db (AsyncSession): The database session.
    """
    # Get the bearer token payload
    payload = decode_bearer_token(token)
    # Add the bearer token to the blacklist
    expires_at = datetime.fromtimestamp(payload.get("exp"))
    blacklisted_token = BlacklistedToken(token=token, expires_at=expires_at)
    db.add(blacklisted_token)
    await db.commit()


async def login_email_password(db: AsyncSession, email: str, password: str) -> str:
    """
    Login a user using email and password.

    Args:
        db (AsyncSession): The database session.
        email (str): The user's email address.
        password (str): The user's password.
    Returns:
        str: The bearer token for the user.
    """
    logger.info(f"Login attempt for user: {email}")

    # Authenticate the user and create a bearer token
    user = await authenticate_user(db, email, password)
    bearer_token_expires = timedelta(minutes=config.bearer_token_expire_minutes)
    bearer_token = create_bearer_token(
        data={"sub": str(user.id)}, expires_delta=bearer_token_expires
    )

    # Log successful login and return the bearer token
    logger.info(f"Successful login for user: {email}")
    return bearer_token


async def is_bearer_token_logged_out(db: AsyncSession, token: str) -> bool:
    """
    Check if a token is logged out.

    Args:
        token (str): The token to check.
        db (AsyncSession): The database session.
    Returns:
        bool: Whether the token is logged out.
    """
    # Check if the token is logged out
    is_logged_out = (await db.execute(
        select(BlacklistedToken).where(
            BlacklistedToken.token == token,
        )
    )).scalar_one_or_none() is not None
    # Return whether the token is logged out
    return is_logged_out


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """
    Authenticate a user.

    Args:
        db (AsyncSession): The database session.
        email (str): The user's email address.
        password (str): The user's password.
    Returns:
        User: The authenticated user, or None if authentication fails.
    Raises:
        UnauthorizedError: If the email or password is invalid
    """
    logger.info(f"Attempting to authenticate user: {email}")

    # Retrieve the user by email and verify the password
    user = await get_user_by_email(db, email)
    if not user or not user.verify_password(password):
        raise UnauthorizedError("Invalid email or password", logger)

    # Log and return the authenticated user
    logger.info(f"Successfully authenticated user: {email}")
    return user
