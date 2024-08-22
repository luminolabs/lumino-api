from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import UserStatus
from app.core.exceptions import UserNotFoundError, EmailAlreadyExistsError
from app.core.cryptography import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.utils import setup_logger

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
    logger.info(f"Attempting to retrieve user with email: {email}")
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user: UserCreate) -> UserResponse:
    """
    Create a new user.

    Args:
        db (AsyncSession): The database session.
        user (UserCreate): The user creation data.
    Returns:
        UserResponse: The newly created user.
    Raises:
        EmailAlreadyExistsError: If a user with the same email already exists.
    """
    logger.info(f"Attempting to create new user with email: {user.email}")

    # Check if a user with the same email already exists
    is_existing_user = await get_user_by_email(db, user.email)
    if is_existing_user:
        raise EmailAlreadyExistsError(f"User with email {user.email} already exists", logger)

    # Hash the user's password and store the user in the database
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, name=user.name, password_hash=hashed_password)
    db.add(db_user)
    await db.commit()

    # Log and return the user
    logger.info(f"Successfully created new user with ID: {db_user.id}")
    return UserResponse.from_orm(db_user)


async def update_user(db: AsyncSession, user: User, user_update: UserUpdate) -> UserResponse:
    """
    Update a user's information.

    Args:
        db (AsyncSession): The database session.
        user (User): The user to update.
        user_update (UserUpdate): The updated user information.
    Returns:
        UserResponse: The updated user.
    """
    logger.info(f"Attempting to update user: {user.id}")

    # Check if a user with the same email already exists
    if user_update.email and user.email != user_update.email:
        is_existing_user = await get_user_by_email(db, user_update.email)
        if is_existing_user:
            raise EmailAlreadyExistsError(f"User with email {user_update.email} already exists", logger)

    # Update the user's information
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    # Commit the changes to the database
    await db.commit()
    await db.refresh(user)  # Refreshes the updated_at field

    # Log and return the updated user
    logger.info(f"Successfully updated user: {user.id}")
    return UserResponse.from_orm(user)


async def deactivate_user(db: AsyncSession, user_id: UUID) -> None:
    """
    Set a user's status to inactive.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user to deactivate.
    Raises:
        UserNotFoundError: If the user is not found.
    """
    logger.info(f"Attempting to delete user: {user_id}")

    # Retrieve the user by ID and raise an error if not found
    db_user = await db.get(User, user_id)
    if not db_user:
        raise UserNotFoundError(f"User with ID {user_id} not found", logger)

    # Set the user's status to inactive and commit the change
    db_user.status = UserStatus.INACTIVE
    await db.commit()

    logger.info(f"Successfully set user {user_id} to inactive status")
