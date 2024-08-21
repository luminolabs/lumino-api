from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional

from app.constants import ApiKeyStatus


class ApiKeyCreate(BaseModel):
    """
    Schema for creating a new API key.
    """
    name: str = Field(..., description="The name of the API key")
    expires_at: datetime = Field(None, description="The expiration date and time of the API key")

class ApiKeyUpdate(BaseModel):
    """
    Schema for updating an existing API key.
    """
    name: Optional[str] = Field(None, description="The new name for the API key")
    expires_at: Optional[datetime] = Field(None, description="The new expiration date and time for the API key")


class ApiKeyResponse(BaseModel):
    """
    Schema for API key response data.
    """
    id: UUID = Field(..., description="The unique identifier of the API key")
    created_at: datetime = Field(..., description="The creation date and time of the API key")
    last_used_at: Optional[datetime] = Field(None, description="The last usage date and time of the API key")
    expires_at: datetime = Field(..., description="The expiration date and time of the API key")
    status: ApiKeyStatus = Field(..., description="The current status of the API key")
    name: str = Field(..., description="The name of the API key")
    prefix: str = Field(..., description="The prefix of the API key (first few characters)")
    model_config = ConfigDict(from_attributes=True)


class ApiKeyWithSecretResponse(ApiKeyResponse):
    """
    Schema for API key response data including the secret key.
    This schema should only be used when creating a new API key to return the secret key to the user.
    """
    secret: str = Field(..., description="The full API key secret")
    model_config = ConfigDict(from_attributes=True)