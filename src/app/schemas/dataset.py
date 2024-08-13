from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from fastapi import UploadFile

from app.constants import DatasetStatus


class DatasetCreate(BaseModel):
    name: str | None = None
    description: str | None = None
    file: UploadFile

    class Config:
        arbitrary_types_allowed = True


class DatasetResponse(BaseModel):
    id: UUID
    created_at: datetime
    status: DatasetStatus
    name: str
    description: str | None
    storage_url: str
    file_size: int
    errors: dict | None
    model_config = ConfigDict(from_attributes=True)


class DatasetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
