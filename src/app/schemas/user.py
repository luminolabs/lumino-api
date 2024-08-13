from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from uuid import UUID

from app.constants import UserStatus


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None


class UserResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    status: UserStatus
    name: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
