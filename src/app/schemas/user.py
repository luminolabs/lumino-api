from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.core.constants import UserStatus

class UserUpdate(BaseModel):
    """
    Schema for updating user information.
    """
    name: str | None = Field(None, min_length=1, max_length=255, description="The updated name of the user")
    email: EmailStr | None = Field(None, description="The updated email address of the user")


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
