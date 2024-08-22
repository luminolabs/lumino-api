from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Dict, Any

from app.core.constants import FineTuningJobStatus


class FineTuningJobCreate(BaseModel):
    """
    Schema for creating a new fine-tuning job.
    """
    base_model_name: str = Field(..., description="The name of the base model to use for fine-tuning")
    dataset_name: str = Field(..., description="The name of the dataset to use for fine-tuning")
    parameters: Dict[str, Any] = Field(..., description="The parameters for the fine-tuning job")
    name: str = Field(..., min_length=1, max_length=255, description="The name of the fine-tuning job")


class FineTuningJobResponse(BaseModel):
    """
    Schema for fine-tuning job response data.
    """
    id: UUID = Field(..., description="The unique identifier of the fine-tuning job")
    created_at: datetime = Field(..., description="The creation date and time of the fine-tuning job")
    updated_at: datetime = Field(..., description="The last update date and time of the fine-tuning job")
    base_model_name: str = Field(..., description="The name of the base model used for fine-tuning")
    dataset_name: str = Field(..., description="The name of the dataset used for fine-tuning")
    status: FineTuningJobStatus = Field(..., description="The current status of the fine-tuning job")
    name: str = Field(..., description="The name of the fine-tuning job")
    current_step: int | None = Field(None, description="The current step of the fine-tuning process")
    total_steps: int | None = Field(None, description="The total number of steps in the fine-tuning process")
    current_epoch: int | None = Field(None, description="The current epoch of the fine-tuning process")
    total_epochs: int | None = Field(None, description="The total number of epochs in the fine-tuning process")
    num_tokens: int | None = Field(None, description="The number of tokens processed in the fine-tuning job")
    model_config = ConfigDict(from_attributes=True)


class FineTuningJobDetailResponse(FineTuningJobResponse):
    """
    Schema for detailed fine-tuning job response data, including parameters and metrics.
    """
    parameters: Dict[str, Any] = Field(..., description="The parameters used for the fine-tuning job")
    metrics: Dict[str, Any] | None = Field(None, description="The metrics collected during the fine-tuning process")
    model_config = ConfigDict(from_attributes=True)
