from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import UserStatus
from app.core.exceptions import UserNotFoundError, EmailAlreadyExistsError
from app.models.user import User
from app.schemas.user import UserUpdate
from app.core.utils import setup_logger
from app.core.authentication import get_user_by_email

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def update_user(db: AsyncSession, user: User, user_update: UserUpdate) -> User:
    """
    Update a user's information.

    Args:
        db (AsyncSession): The database session.
        user (User): The user to update.
        user_update (UserUpdate): The updated user information.
    Returns:
        User: The updated user.
    """
    logger.info(f"Attempting to update user: {user.id}")

    # Update the user's information
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    # Commit the changes to the database
    await db.commit()
    await db.refresh(user)  # Refreshes the updated_at field

    # Log and return the updated user
    logger.info(f"Successfully updated user: {user.id}")
    return user


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
