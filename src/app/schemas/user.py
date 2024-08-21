from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.constants import UserStatus


class UserCreate(BaseModel):
    """
    Schema for creating a new user.
    """
    name: str = Field(..., description="The name of the user")
    email: EmailStr = Field(..., description="The email address of the user")
    password: str = Field(..., description="The password for the user account")


class UserUpdate(BaseModel):
    """
    Schema for updating user information.
    """
    name: Optional[str] = Field(None, description="The updated name of the user")
    email: Optional[EmailStr] = Field(None, description="The updated email address of the user")


class UserResponse(BaseModel):
    """
    Schema for user response data.
    """
    id: UUID = Field(..., description="The unique identifier for the user")
    created_at: datetime = Field(..., description="The timestamp when the user was created")
    updated_at: datetime = Field(..., description="The timestamp when the user was last updated")
    status: UserStatus = Field(..., description="The current status of the user")
    name: str = Field(..., description="The name of the user")
    email: EmailStr = Field(..., description="The email address of the user")
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    """
    Schema for user login request.
    """
    email: EmailStr = Field(..., description="The email address for login")
    password: str = Field(..., description="The password for login")


class LoginResponse(BaseModel):
    """
    Schema for login response.
    """
    access_token: str = Field(..., description="The JWT access token")
    token_type: str = Field(..., description="The type of the token (e.g., 'bearer')")
    expires_in: int = Field(..., description="The expiration time of the token in seconds")
    model_config = ConfigDict(from_attributes=True)
