from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from fastapi import UploadFile

from app.constants import DatasetStatus


class DatasetCreate(BaseModel):
    """
    Schema for creating a new dataset.

    Attributes:
        name (str): The name of the dataset.
        description (str | None): An optional description of the dataset.
        file (UploadFile): The uploaded dataset file.
    """
    name: str = Field(..., description="The name of the dataset")
    description: str | None = Field(None, description="An optional description of the dataset")
    file: UploadFile

    class Config:
        arbitrary_types_allowed = True


class DatasetResponse(BaseModel):
    """
    Schema for dataset response data.

    Attributes:
        id (UUID): The unique identifier of the dataset.
        created_at (datetime): The timestamp when the dataset was created.
        status (DatasetStatus): The current status of the dataset.
        name (str): The name of the dataset.
        description (str | None): The description of the dataset, if any.
        storage_url (str): The URL where the dataset file is stored.
        file_size (int): The size of the dataset file in bytes.
        errors (dict | None): Any errors encountered during dataset processing, if any.
    """
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
    """
    Schema for updating an existing dataset.

    Attributes:
        name (str | None): The new name for the dataset (optional).
        description (str | None): The new description for the dataset (optional).
    """
    name: str | None = Field(None, description="The new name for the dataset")
    description: str | None = Field(None, description="The new description for the dataset")