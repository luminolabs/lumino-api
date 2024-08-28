from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime, timezone
from uuid import UUID

from app.core.constants import ApiKeyStatus
from app.core.exceptions import BadRequestError


def _expiration_must_be_future(v: datetime) -> datetime:
    if v.astimezone(timezone.utc) <= datetime.utcnow().astimezone(timezone.utc):
        raise BadRequestError('Expiration date must be in the future')
    return v


class ApiKeyCreate(BaseModel):
    """
    Schema for creating a new API key.
    """
    name: str = Field(..., min_length=1, max_length=255, description="The name of the API key")
    expires_at: datetime = Field(..., description="The expiration date and time of the API key")

    @field_validator('expires_at')
    def expiration_must_be_future(cls, v: datetime) -> datetime:
        return _expiration_must_be_future(v)


class ApiKeyUpdate(BaseModel):
    """
    Schema for updating an existing API key.
    """
    name: str | None = Field(None, min_length=1, max_length=255, description="The new name for the API key")
    expires_at: datetime | None = Field(None, description="The new expiration date and time for the API key")

    @field_validator('expires_at')
    def expiration_must_be_future(cls, v: datetime) -> datetime:
        return _expiration_must_be_future(v)


class ApiKeyResponse(BaseModel):
    """
    Schema for API key response data.
    """
    id: UUID = Field(..., description="The unique identifier of the API key")
    created_at: datetime = Field(..., description="The creation date and time of the API key")
    last_used_at: datetime | None = Field(None, description="The last usage date and time of the API key")
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
