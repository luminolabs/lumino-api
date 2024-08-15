from uuid import UUID

from fastapi import Depends
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.constants import UserStatus
from app.core.authentication import oauth2_scheme
from app.core.exceptions import UserNotFoundError, EmailAlreadyExistsError, UnauthorizedError
from app.core.security import verify_password, get_password_hash, SECRET_KEY, ALGORITHM
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.utils import setup_logger

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    Retrieve a user by email.
    """
    logger.info(f"Attempting to retrieve user with email: {email}")
    result = await db.execute(select(User).where(User.email == email, User.status == UserStatus.ACTIVE))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user: UserCreate) -> UserResponse:
    """
    Create a new user.
    """
    logger.info(f"Attempting to create new user with email: {user.email}")
    existing_user = await get_user_by_email(db, user.email)
    if existing_user:
        logger.warning(f"Attempt to create user with existing email: {user.email}")
        raise EmailAlreadyExistsError()

    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, name=user.name, password_hash=hashed_password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info(f"Successfully created new user with ID: {db_user.id}")
    return UserResponse.from_orm(db_user)


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """
    Authenticate a user.
    """
    logger.info(f"Attempting to authenticate user: {email}")
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        logger.warning(f"Failed authentication attempt for user: {email}")
        return None
    logger.info(f"Successfully authenticated user: {email}")
    return user


async def get_current_active_user(
        db: AsyncSession = Depends(get_db),
        token: str = Depends(oauth2_scheme)
) -> UserResponse:
    """
    Get the current authenticated user.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token payload does not contain user ID")
            raise UnauthorizedError()
    except JWTError:
        logger.error("Failed to decode JWT token")
        raise UnauthorizedError()

    user = await db.get(User, UUID(user_id))
    if user is None:
        logger.warning(f"No user found for ID: {user_id}")
        raise UserNotFoundError()
    if user.status != UserStatus.ACTIVE:
        logger.warning(f"Attempt to authenticate inactive user: {user_id}")
        raise UnauthorizedError("Inactive user")
    logger.info(f"Successfully retrieved current active user: {user_id}")
    return UserResponse.from_orm(user)


async def update_user(db: AsyncSession, user_id: UUID, user_update: UserUpdate) -> UserResponse:
    """
    Update a user's information.
    """
    logger.info(f"Attempting to update user: {user_id}")
    db_user = await db.get(User, user_id)
    if not db_user:
        logger.warning(f"Attempt to update non-existent user: {user_id}")
        raise UserNotFoundError()

    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)

    await db.commit()
    await db.refresh(db_user)
    logger.info(f"Successfully updated user: {user_id}")
    return UserResponse.from_orm(db_user)


async def delete_user(db: AsyncSession, user_id: UUID) -> None:
    """
    Set a user's status to inactive.
    """
    logger.info(f"Attempting to delete user: {user_id}")
    db_user = await db.get(User, user_id)
    if not db_user:
        logger.warning(f"Attempt to delete non-existent user: {user_id}")
        raise UserNotFoundError()

    db_user.status = UserStatus.INACTIVE
    await db.commit()
    logger.info(f"Successfully set user {user_id} to inactive status")
