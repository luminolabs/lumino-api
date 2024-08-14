from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, ConfigDict

from app.constants import UserStatus


class UserCreate(BaseModel):
    """
    Schema for creating a new user.

    Attributes:
        name (str): The name of the user.
        email (EmailStr): The email address of the user.
        password (str): The password for the user account.
    """
    name: str
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """
    Schema for updating user information.

    Attributes:
        name (str | None): The updated name of the user (optional).
        email (EmailStr | None): The updated email address of the user (optional).
    """
    name: str | None = None
    email: EmailStr | None = None


class UserResponse(BaseModel):
    """
    Schema for user response data.

    Attributes:
        id (UUID): The unique identifier for the user.
        created_at (datetime): The timestamp when the user was created.
        updated_at (datetime): The timestamp when the user was last updated.
        status (UserStatus): The current status of the user.
        name (str): The name of the user.
        email (EmailStr): The email address of the user.
    """
    id: UUID
    created_at: datetime
    updated_at: datetime
    status: UserStatus
    name: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    """
    Schema for user login request.

    Attributes:
        email (EmailStr): The email address for login.
        password (str): The password for login.
    """
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """
    Schema for login response.

    Attributes:
        access_token (str): The JWT access token.
        token_type (str): The type of the token (e.g., "bearer").
        expires_in (int): The expiration time of the token in seconds.
    """
    access_token: str
    token_type: str
    expires_in: int
