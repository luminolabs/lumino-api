from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from typing import Optional

from app.config_manager import config
from app.core.security import create_access_token, SECRET_KEY, ALGORITHM
from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, LoginRequest
from app.services.user import (
    create_user,
    authenticate_user,
    update_user,
    delete_user,
)
from app.models.blacklisted_token import BlacklistedToken
from app.core.authentication import get_current_active_user, oauth2_scheme, get_api_key

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
        )
    access_token_expires = timedelta(minutes=config.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
        current_user: UserResponse = Depends(get_current_active_user)
) -> UserResponse:
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
async def logout(
        current_user: UserResponse = Depends(get_current_active_user),
        token: str = Depends(oauth2_scheme),
        api_key: Optional[str] = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
):
    """
    Log out the current user by blacklisting their token.
    """
    # If authenticated with API key, we don't need to blacklist anything
    if api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Can't logout using an api key",
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        expires_at = datetime.fromtimestamp(payload.get("exp"))
        blacklisted_token = BlacklistedToken(token=token, expires_at=expires_at)
        db.add(blacklisted_token)
        await db.commit()
        return {"detail": "Successfully logged out"}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

@router.post("/users/password-reset")
async def request_password_reset(email: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Request a password reset for a user.
    """
    # TODO: Implement password reset logic
    return {"detail": "Password reset email sent"}

@router.post("/users/password-reset/{token}")
async def reset_password(token: str, new_password: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Reset a user's password using a reset token.
    """
    # TODO: Implement password reset logic
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
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")
    try:
        await delete_user(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
