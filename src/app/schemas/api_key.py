from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from app.constants import ApiKeyStatus


class ApiKeyCreate(BaseModel):
    name: str
    expires_at: datetime | None = None


class ApiKeyUpdate(BaseModel):
    name: str | None = None
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: UUID
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    status: ApiKeyStatus
    name: str
    prefix: str


class ApiKeyWithSecret(ApiKeyResponse):
    secret: str
