from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from fastapi import UploadFile


class DatasetCreate(BaseModel):
    id: str | None = None
    description: str | None = None
    file: UploadFile

    class Config:
        arbitrary_types_allowed = True


class DatasetResponse(BaseModel):
    id: UUID
    created_at: datetime
    user_id: UUID
    status: str
    description: str | None
    storage_url: str
    file_size: int
    errors: dict | None


class DatasetUpdate(BaseModel):
    description: str | None = None
