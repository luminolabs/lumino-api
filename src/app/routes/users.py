from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, LoginRequest
from app.services.user import (
    create_user,
    authenticate_user,
    get_current_user,
    update_user,
    delete_user,
)

router = APIRouter(tags=["Users"])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """
    Create a new user account.

    Args:
        user (UserCreate): The user data for creating a new account.
        db (AsyncSession): The database session.

    Returns:
        UserResponse: The created user's data.

    Raises:
        HTTPException: If there's an error creating the user.
    """
    try:
        return await create_user(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/login", response_model=dict)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Authenticate a user and return an access token.

    Args:
        login_data (LoginRequest): The user's login credentials.
        db (AsyncSession): The database session.

    Returns:
        dict: A dictionary containing the access token and token type.

    Raises:
        HTTPException: If authentication fails.
    """
    user = await authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # TODO: Implement JWT token generation
    return {"access_token": "dummy_token", "token_type": "bearer"}


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """
    Get the current user's information.

    Args:
        current_user (UserResponse): The current authenticated user.

    Returns:
        UserResponse: The current user's data.
    """
    return current_user


@router.patch("/users/me", response_model=UserResponse)
async def update_current_user(
        user_update: UserUpdate,
        current_user: UserResponse = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Update the current user's information.

    Args:
        user_update (UserUpdate): The user data to be updated.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        UserResponse: The updated user's data.

    Raises:
        HTTPException: If there's an error updating the user.
    """
    try:
        return await update_user(db, current_user.id, user_update)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(user_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a user account (Internal API).

    Args:
        user_id (UUID): The ID of the user to be deleted.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If there's an error deleting the user or if the user is not found.
    """
    # TODO: Implement proper authentication for internal API
    try:
        await delete_user(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/users/logout")
async def logout() -> dict:
    """
    Log out the current user.

    Returns:
        dict: A message confirming successful logout.
    """
    # TODO: Implement token invalidation or session management
    return {"message": "Successfully logged out"}


@router.post("/users/password-reset")
async def request_password_reset(email: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Request a password reset for a user.

    Args:
        email (str): The email of the user requesting a password reset.
        db (AsyncSession): The database session.

    Returns:
        dict: A message confirming the password reset email has been sent.
    """
    # TODO: Implement password reset logic
    return {"message": "Password reset email sent"}


@router.post("/users/password-reset/{token}")
async def reset_password(token: str, new_password: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Reset a user's password using a reset token.

    Args:
        token (str): The password reset token.
        new_password (str): The new password for the user.
        db (AsyncSession): The database session.

    Returns:
        dict: A message confirming the password has been reset.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    # TODO: Implement password reset logic
    return {"message": "Password has been reset successfully"}
