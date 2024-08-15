from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from uuid import UUID
from typing import Optional

from app.constants import ApiKeyStatus


class ApiKeyCreate(BaseModel):
    """
    Schema for creating a new API key.

    Attributes:
        name (str): The name of the API key.
        expires_at (Optional[datetime]): The expiration date and time of the API key.
    """
    name: str = Field(..., description="The name of the API key")
    expires_at: Optional[datetime] = Field(None, description="The expiration date and time of the API key")

    class Config:
        json_encoders = {
            datetime: lambda v: v.replace(tzinfo=ZoneInfo("UTC")).isoformat()
        }

class ApiKeyUpdate(BaseModel):
    """
    Schema for updating an existing API key.

    Attributes:
        name (Optional[str]): The new name for the API key.
        expires_at (Optional[datetime]): The new expiration date and time for the API key.
    """
    name: Optional[str] = Field(None, description="The new name for the API key")
    expires_at: Optional[datetime] = Field(None, description="The new expiration date and time for the API key")

    class Config:
        json_encoders = {
            datetime: lambda v: v.replace(tzinfo=ZoneInfo("UTC")).isoformat()
        }


class ApiKeyResponse(BaseModel):
    """
    Schema for API key response data.

    Attributes:
        id (UUID): The unique identifier of the API key.
        created_at (datetime): The creation date and time of the API key.
        last_used_at (Optional[datetime]): The last usage date and time of the API key.
        expires_at (Optional[datetime]): The expiration date and time of the API key.
        status (ApiKeyStatus): The current status of the API key.
        name (str): The name of the API key.
        prefix (str): The prefix of the API key (first few characters).
    """
    id: UUID
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: ApiKeyStatus
    name: str
    prefix: str
    model_config = ConfigDict(from_attributes=True)


class ApiKeyWithSecret(ApiKeyResponse):
    """
    Schema for API key response data including the secret key.
    This schema should only be used when creating a new API key.

    Attributes:
        secret (str): The full API key secret.
    """
    secret: str = Field(..., description="The full API key secret")