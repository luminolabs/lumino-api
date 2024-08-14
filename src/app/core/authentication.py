from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.core.security import SECRET_KEY, ALGORITHM
from app.schemas.user import UserResponse
from app.services.api_key import verify_api_key
from uuid import UUID

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Get the current authenticated user based on the JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.get(User, UUID(user_id))
    if user is None:
        raise credentials_exception
    return UserResponse.from_orm(user)


async def get_current_active_user(
        current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Get the current active user.
    """
    if current_user.status != "active":
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_api_key_user(
        api_key: str,
        db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Get the user associated with an API key.
    """
    user_id = await verify_api_key(db, api_key)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return UserResponse.from_orm(user)


def get_current_user_or_api_key(
        token: str = Depends(oauth2_scheme),
        api_key: str | None = None,
        db: AsyncSession = Depends(get_db)
):
    """
    Get the current user from either JWT token or API key.
    """
    async def auth_user():
        if api_key:
            return await get_api_key_user(api_key, db)
        return await get_current_user(token, db)

    return auth_user()
