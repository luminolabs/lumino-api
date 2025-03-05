from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.schemas.common import DateTime


class WhitelistRequestCreate(BaseModel):
    """
    Schema for creating a new whitelist request.
    """
    name: str = Field(..., min_length=1, max_length=255, description="The name of the requestor")
    email: EmailStr = Field(..., description="The email of the requestor")
    phone_number: str = Field(..., min_length=5, max_length=20, description="The phone number of the requestor")


class WhitelistRequestUpdate(BaseModel):
    """
    Schema for updating a whitelist request. Admin only.
    """
    is_whitelisted: bool | None = Field(None, description="Whether the user is whitelisted")
    has_signed_nda: bool | None = Field(None, description="Whether the user has signed the NDA")


class WhitelistRequestResponse(BaseModel):
    """
    Schema for whitelist request response data.
    """
    id: UUID = Field(..., description="The unique identifier for the whitelist request")
    created_at: DateTime = Field(..., description="The timestamp when the whitelist request was created")
    updated_at: DateTime = Field(..., description="The timestamp when the whitelist request was last updated")
    user_id: UUID = Field(..., description="The ID of the user who made the whitelist request")
    name: str = Field(..., description="The name provided in the whitelist request")
    email: EmailStr = Field(..., description="The email provided in the whitelist request")
    phone_number: str = Field(..., description="The phone number provided in the whitelist request")
    is_whitelisted: bool = Field(..., description="Whether the user is whitelisted or not")
    has_signed_nda: bool = Field(..., description="Whether the user has signed the NDA or not")
    model_config = ConfigDict(from_attributes=True)