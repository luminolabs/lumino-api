from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class ApiKeyCreate(BaseModel):
    name: str
    expires_at: datetime | None = None


class ApiKeyUpdate(BaseModel):
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: UUID
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    status: str
    name: str
    prefix: str


class ApiKeyWithSecret(ApiKeyResponse):
    secret: str
