from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.core.authentication import get_current_active_user, oauth2_scheme, get_api_key, logout_bearer_token, \
    login_email_password
from app.core.exceptions import (
    BadRequestError,
    ForbiddenError,
)
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, LoginRequest
from app.services.user import (
    create_user,
    update_user,
    deactivate_user,
)
from app.utils import setup_logger

# Set up API router
router = APIRouter(tags=["Users"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """
    Create a new user account.

    Args:
        user (UserCreate): The user creation data.
        db (AsyncSession): The database session.
    """
    new_user = await create_user(db, user)
    return new_user


@router.post("/users/login", response_model=dict)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Authenticate a user and return an access token.

    Args:
        login_data (LoginRequest): The user login data.
        db (AsyncSession): The database session.
    """
    bearer_token = await login_email_password(db, login_data.email, login_data.password)
    return {"access_token": bearer_token, "token_type": "bearer"}


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
    return updated_user


@router.post("/users/logout")
async def logout(
        current_user: User = Depends(get_current_active_user),
        token: str = Depends(oauth2_scheme),
        api_key: Optional[str] = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
):
    """
    Log out the current user by blacklisting their bearer token.

    Args:
        current_user (User): The current authenticated user.
        token (str): The bearer token to blacklist.
        api_key (str): The API key if present.
        db (AsyncSession): The database session.
    Raises:
        BadRequestError: If the user tries to log out using an API key.
    """
    if api_key:
        logger.warning(f"Logout attempt using API key for user: {current_user.id}")
        raise BadRequestError(f"Can't logout using an API key, "
                              f"only with bearer token: {api_key[:8]}...", logger)
    
    await logout_bearer_token(token, db)
    return {"message": "Successfully logged out"}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user_route(
        user_id: str,
        current_user: User = Depends(get_current_active_user),
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
    if str(current_user.id) != config.admin_user_id:
        raise ForbiddenError(f"Unauthorized deactivation attempt of user {user_id} "
                             f"by user {current_user.id}", logger)
    await deactivate_user(db, user_id)
