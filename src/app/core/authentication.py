from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.constants import UserStatus
from app.core.exceptions import UnauthorizedError, InvalidTokenError, ExpiredTokenError, UserNotFoundError
from app.core.security import SECRET_KEY, ALGORITHM
from app.database import get_db
from app.models.api_key import ApiKey
from app.models.blacklisted_token import BlacklistedToken
from app.models.user import User
from app.schemas.user import UserResponse
from app.utils import setup_logger

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


async def is_token_blacklisted(db: AsyncSession, token: str) -> bool:
    """
    Check if a token is logged out.
    """
    result = await db.execute(
        select(BlacklistedToken).where(
            BlacklistedToken.token == token,
        )
    )
    is_blacklisted = result.scalar_one_or_none() is not None
    if is_blacklisted:
        logger.warning(f"Attempt to use logged out token: {token[:10]}...")
    return is_blacklisted


async def get_user_from_api_key(db: AsyncSession, api_key: str) -> User | None:
    """
    Get a user from an API key.
    """
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.prefix == api_key[:8],
            ApiKey.status == 'ACTIVE',
            ApiKey.expires_at > datetime.utcnow()
        )
    )
    db_api_key = result.scalar_one_or_none()
    if db_api_key and db_api_key.verify_key(api_key):
        user = await db.get(User, db_api_key.user_id)
        if user:
            logger.info(f"User authenticated via API key: {user.id}")
            return user
    logger.warning(f"Failed authentication attempt with API key: {api_key[:8]}...")
    return None


async def get_user_from_jwt(token: str, db: AsyncSession) -> User | None:
    """
    Get a user from a JWT token.
    """
    try:
        if await is_token_blacklisted(db, token):
            logger.warning(f"Attempt to use logged out JWT token: {token[:10]}...")
            raise ExpiredTokenError("Token has been logged out")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("JWT token payload does not contain user ID")
            raise InvalidTokenError("Invalid token payload")
        user = await db.get(User, UUID(user_id))
        if user and user.status == UserStatus.ACTIVE:
            logger.info(f"User authenticated via JWT: {user.id}")
            return user
        logger.warning(f"User not found or inactive for JWT token: {token[:10]}...")
        raise UserNotFoundError("User not found or inactive")
    except JWTError:
        logger.error(f"Invalid JWT token: {token[:10]}...")
        raise InvalidTokenError("Invalid token")


async def get_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """
    Get the API key from the request header.
    """
    return x_api_key


async def get_current_active_user(
        token: str = Depends(oauth2_scheme),
        api_key: Optional[str] = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Get the current active user from either a JWT token or an API key.
    """
    if api_key:
        user = await get_user_from_api_key(db, api_key)
        if user and user.status == UserStatus.ACTIVE:
            return UserResponse.from_orm(user)
        logger.warning("Failed authentication attempt with API key")
        raise UnauthorizedError("Invalid API key")

    if not token:
        logger.warning("No token provided for authentication")
        raise UnauthorizedError("No authentication token provided")

    try:
        user = await get_user_from_jwt(token, db)
        return UserResponse.from_orm(user)
    except (InvalidTokenError, ExpiredTokenError, UserNotFoundError) as e:
        logger.warning(f"Failed authentication attempt with JWT: {str(e)}")
        raise UnauthorizedError(str(e))


async def logout_user(token: str, db: AsyncSession):
    """
    Blacklist a JWT token.
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    expires_at = datetime.fromtimestamp(payload.get("exp"))
    blacklisted_token = BlacklistedToken(token=token, expires_at=expires_at)
    db.add(blacklisted_token)
    await db.commit()