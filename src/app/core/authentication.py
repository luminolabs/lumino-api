from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional

from app.constants import UserStatus
from app.database import get_db
from app.models.user import User
from app.models.blacklisted_token import BlacklistedToken
from app.models.api_key import ApiKey
from app.core.security import SECRET_KEY, ALGORITHM
from app.schemas.user import UserResponse
from uuid import UUID

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

async def is_token_blacklisted(db: AsyncSession, token: str) -> bool:
    result = await db.execute(
        select(BlacklistedToken).where(
            BlacklistedToken.token == token,
        )
    )
    return result.scalar_one_or_none() is not None

async def get_user_from_api_key(db: AsyncSession, api_key: str) -> User | None:
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.prefix == api_key[:8],
            ApiKey.status == 'ACTIVE',
            ApiKey.expires_at > datetime.utcnow()
        )
    )
    db_api_key = result.scalar_one_or_none()
    if db_api_key and db_api_key.verify_key(api_key):
        return await db.get(User, db_api_key.user_id)
    return None

async def get_user_from_jwt(token: str, db: AsyncSession) -> User | None:
    try:
        if await is_token_blacklisted(db, token):
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        user = await db.get(User, UUID(user_id))
        return user if user and user.status == UserStatus.ACTIVE else None
    except JWTError:
        return None

async def get_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    return x_api_key

async def get_current_active_user(
        token: str = Depends(oauth2_scheme),
        api_key: Optional[str] = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Check for API key
    if api_key:
        user = await get_user_from_api_key(db, api_key)
        if user and user.status == UserStatus.ACTIVE:
            return UserResponse.from_orm(user)
        raise credentials_exception

    # If no API key, proceed with JWT token authentication
    if not token:
        raise credentials_exception

    user = await get_user_from_jwt(token, db)
    if user is None:
        raise credentials_exception

    return UserResponse.from_orm(user)
