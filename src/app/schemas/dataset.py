from uuid import UUID

from fastapi import UploadFile
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.core.constants import DatasetStatus
from app.core.exceptions import BadRequestError
from app.schemas.common import NameField, DateTime


class DatasetCreate(BaseModel):
    """
    Schema for creating a new dataset.
    """
    name: str = NameField(..., description="The name of the dataset")
    description: str | None = Field(None, max_length=1000, description="A description of the dataset")
    file: UploadFile = Field(..., description="The uploaded dataset file")

    @field_validator('file')
    def validate_file_size(cls, v):
        max_size = 100 * 1024 * 1024  # 100 MB
        if v.size > max_size:
            raise BadRequestError(f"File size must not exceed {max_size} bytes, got {v.size} bytes")
        return v


class DatasetUpdate(BaseModel):
    """
    Schema for updating an existing dataset.
    """
    name: str | None = NameField(None, description="The new name for the dataset")
    description: str | None = Field(None, max_length=1000, description="The new description for the dataset")


class DatasetResponse(BaseModel):
    """
    Schema for dataset response data.
    """
    id: UUID = Field(..., description="The unique identifier of the dataset")
    created_at: DateTime = Field(..., description="The timestamp when the dataset was created")
    updated_at: DateTime = Field(..., description="The timestamp when the dataset was last updated")
    status: DatasetStatus = Field(..., description="The current status of the dataset")
    name: str = Field(..., description="The name of the dataset")
    description: str | None = Field(None, description="The description of the dataset, if any")
    file_name: str = Field(..., description="The name of the stored dataset file")
    file_size: int = Field(..., description="The size of the dataset file in bytes")
    errors: dict | None = Field(None, description="Any errors encountered during dataset processing, if any")
    model_config = ConfigDict(from_attributes=True)
