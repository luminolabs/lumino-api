from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.core.security import create_access_token
from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, LoginRequest
from app.services.user import (
    create_user,
    authenticate_user,
    get_current_active_user,
    update_user, delete_user,
)

router = APIRouter(tags=["Users"])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """
    Create a new user account.
    """
    try:
        return await create_user(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/login", response_model=dict)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Authenticate a user and return an access token.
    """
    user = await authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=config.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_active_user)) -> UserResponse:
    """
    Get the current user's information.
    """
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
        return await update_user(db, current_user.id, user_update)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/logout")
async def logout() -> dict:
    """
    Log out the current user.
    """
    # TODO: Implement token invalidation or session management
    return {"message": "Successfully logged out"}


@router.post("/users/password-reset")
async def request_password_reset(email: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Request a password reset for a user.
    """
    # TODO: Implement password reset logic
    return {"message": "Password reset email sent"}


@router.post("/users/password-reset/{token}")
async def reset_password(token: str, new_password: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Reset a user's password using a reset token.
    """
    # TODO: Implement password reset logic
    return {"message": "Password has been reset successfully"}


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
) -> None:
    """
    Set the current user's account to inactive.
    """
    try:
        await delete_user(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
