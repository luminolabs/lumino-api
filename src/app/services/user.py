from uuid import UUID
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import oauth2_scheme
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.security import verify_password, get_password_hash, SECRET_KEY, ALGORITHM


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Retrieve a user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user: UserCreate) -> UserResponse:
    """Create a new user."""
    existing_user = await get_user_by_email(db, user.email)
    if existing_user:
        raise ValueError("Email already registered")

    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, name=user.name, password_hash=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return UserResponse.from_orm(db_user)


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Authenticate a user."""
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_active_user(
        db: AsyncSession = Depends(get_db),
        token: str = Depends(oauth2_scheme)
) -> UserResponse:
    """Get the current authenticated user."""
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
    if user.status != "active":
        raise HTTPException(status_code=400, detail="Inactive user")
    return UserResponse.from_orm(user)


async def update_user(db: AsyncSession, user_id: UUID, user_update: UserUpdate) -> UserResponse:
    """Update a user's information."""
    db_user = await db.get(User, user_id)
    if not db_user:
        raise ValueError("User not found")

    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)

    await db.commit()
    await db.refresh(db_user)
    return UserResponse.from_orm(db_user)


async def delete_user(db: AsyncSession, user_id: UUID) -> None:
    """Set a user's status to inactive."""
    db_user = await db.get(User, user_id)
    if not db_user:
        raise ValueError("User not found")

    db_user.status = "inactive"
    await db.commit()
