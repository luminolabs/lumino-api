from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import get_current_active_user, admin_required
from app.core.config_manager import config
from app.core.database import get_db
from app.core.utils import setup_logger
from app.models.user import User
from app.schemas.user import UserUpdate, UserResponse
from app.services.user import update_user, deactivate_user

# Set up API router
router = APIRouter(tags=["Users"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
        current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get the current user's information.

    Args:
        current_user (User): The current authenticated user.
    """
    logger.info(f"Retrieving information for user: {current_user.id}")
    return UserResponse.from_orm(current_user)


@router.patch("/users/me", response_model=UserResponse)
async def update_current_user(
        user_update: UserUpdate,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update the current user's information.

    Args:
        user_update (UserUpdate): The updated user information.
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.
    """
    updated_user = await update_user(db, current_user, user_update)
    return UserResponse.from_orm(updated_user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user_route(
        user_id: str,
        # This is an admin only action, don't remove the `admin_required` dependency
        current_user: User = Depends(admin_required),
        db: AsyncSession = Depends(get_db)
) -> None:
    """
    Set the current user's account to inactive.

    Args:
        user_id (str): The ID of the user to deactivate.
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.
    Raises:
        ForbiddenError: If the current user is not an admin.
    """
    await deactivate_user(db, UUID(user_id))
