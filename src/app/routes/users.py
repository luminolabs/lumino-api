from datetime import timedelta, datetime
from typing import Optional

from fastapi import APIRouter, Depends, status
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.core.authentication import get_current_active_user, oauth2_scheme, get_api_key
from app.core.exceptions import (
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    EmailAlreadyExistsError,
    UserNotFoundError,
    InvalidTokenError
)
from app.core.security import create_access_token, SECRET_KEY, ALGORITHM
from app.database import get_db
from app.models.blacklisted_token import BlacklistedToken
from app.schemas.user import UserCreate, UserUpdate, UserResponse, LoginRequest
from app.services.user import (
    create_user,
    authenticate_user,
    update_user,
    delete_user,
)
from app.utils import setup_logger

router = APIRouter(tags=["Users"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """
    Create a new user account.
    """
    try:
        logger.info(f"Attempting to create new user with email: {user.email}")
        new_user = await create_user(db, user)
        logger.info(f"Successfully created new user with ID: {new_user.id}")
        return new_user
    except EmailAlreadyExistsError as e:
        logger.error(f"Error creating user: {str(e)}")
        raise BadRequestError(str(e))


@router.post("/users/login", response_model=dict)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Authenticate a user and return an access token.
    """
    logger.info(f"Login attempt for user: {login_data.email}")
    user = await authenticate_user(db, login_data.email, login_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {login_data.email}")
        raise UnauthorizedError("Incorrect email or password")
    access_token_expires = timedelta(minutes=config.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    logger.info(f"Successful login for user: {login_data.email}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
        current_user: UserResponse = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get the current user's information.
    """
    logger.info(f"Retrieving information for user: {current_user.id}")
    return current_user


@router.patch("/users/me", response_model=UserResponse)
async def update_current_user(
        user_update: UserUpdate,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update the current user's information.
    """
    try:
        logger.info(f"Updating information for user: {current_user.id}")
        updated_user = await update_user(db, current_user.id, user_update)
        logger.info(f"Successfully updated user: {current_user.id}")
        return updated_user
    except UserNotFoundError as e:
        logger.error(f"Error updating user {current_user.id}: {str(e)}")
        raise NotFoundError(str(e))


@router.post("/users/logout")
async def logout(
        current_user: UserResponse = Depends(get_current_active_user),
        token: str = Depends(oauth2_scheme),
        api_key: Optional[str] = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
):
    """
    Log out the current user by blacklisting their token.
    """
    if api_key:
        logger.warning(f"Logout attempt using API key for user: {current_user.id}")
        raise UnauthorizedError("Can't logout using an API key")

    if not token:
        logger.error(f"Logout attempt without token for user: {current_user.id}")
        raise UnauthorizedError("No token provided")

    try:
        logger.info(f"Logging out user: {current_user.id}")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        expires_at = datetime.fromtimestamp(payload.get("exp"))
        blacklisted_token = BlacklistedToken(token=token, expires_at=expires_at)
        db.add(blacklisted_token)
        await db.commit()
        logger.info(f"Successfully logged out user: {current_user.id}")
        return {"detail": "Successfully logged out"}
    except JWTError:
        logger.error(f"Error during logout for user: {current_user.id}")
        raise InvalidTokenError("Invalid token")


@router.post("/users/password-reset")
async def request_password_reset(email: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Request a password reset for a user.
    """
    # TODO: Implement password reset logic
    logger.info(f"Password reset requested for email: {email}")
    return {"detail": "Password reset email sent"}


@router.post("/users/password-reset/{token}")
async def reset_password(token: str, new_password: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Reset a user's password using a reset token.
    """
    # TODO: Implement password reset logic
    logger.info("Password reset attempt")
    return {"detail": "Password has been reset successfully"}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
        user_id: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> None:
    """
    Set the current user's account to inactive.
    """
    if str(current_user.id) != user_id:
        logger.warning(f"Unauthorized deletion attempt of user {user_id} by user {current_user.id}")
        raise ForbiddenError("Not authorized to delete this user")
    try:
        logger.info(f"Deleting user account: {user_id}")
        await delete_user(db, user_id)
        logger.info(f"Successfully deleted user account: {user_id}")
    except UserNotFoundError as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise NotFoundError(str(e))
