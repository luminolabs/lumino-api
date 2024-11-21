from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import UserStatus, BillingTransactionType
from app.core.exceptions import UserNotFoundError
from app.core.stripe_client import create_stripe_customer
from app.core.utils import setup_logger
from app.models.user import User
from app.queries import users as user_queries
from app.schemas.user import UserUpdate, UserResponse
from app.services.billing import add_credits_to_user

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def update_user(db: AsyncSession, user_id: UUID, user_update: UserUpdate) -> UserResponse:
    """Update a user's information."""
    logger.info(f"Attempting to update user: {user_id}")

    # Get user
    user = await user_queries.get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(f"User with ID {user_id} not found", logger)

    # Update the user's information
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    logger.info(f"Successfully updated user: {user_id}")
    return UserResponse.from_orm(user)


async def deactivate_user(db: AsyncSession, user_id: UUID) -> None:
    """Set a user's status to inactive."""
    logger.info(f"Attempting to deactivate user: {user_id}")

    # Get user
    user = await user_queries.get_user_by_id(db, user_id)
    if not user:
        raise UserNotFoundError(f"User with ID {user_id} not found", logger)

    # Set status to inactive
    user.status = UserStatus.INACTIVE
    await db.commit()

    logger.info(f"Successfully deactivated user: {user_id}")


async def create_user(db: AsyncSession, name: str, email: str,
                      auth0_user_id: str, email_verified: bool) -> User:
    """Create a new user."""
    try:
        # Create the new user
        db_user = User(
            email=email,
            name=name,
            auth0_user_id=auth0_user_id,
            email_verified=email_verified
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        # Add new user credits
        free_credits = float(config.new_user_credits)
        if config.new_user_credits:
            await add_credits_to_user(
                db, db_user.id, free_credits,
                "NEW_USER_CREDIT", BillingTransactionType.NEW_USER_CREDIT
            )

        # Create a Stripe customer
        await create_stripe_customer(db, db_user)

        logger.info(f"Successfully created new user with ID: {db_user.id}")
        return db_user

    except Exception as e:
        await db.rollback()
        raise e
