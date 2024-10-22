from typing import Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.core.constants import FineTuningJobStatus, FineTuningJobType, ComputeProvider
from app.schemas.common import NameField, DateTime


class FineTuningJobParameters(BaseModel):
    """Model for fine-tuning job parameters."""
    batch_size: int = Field(default=2, gt=0, le=8)
    shuffle: bool = Field(default=True)
    num_epochs: int = Field(default=1, gt=0, le=10)
    lr: float = Field(default=3e-4, gt=0, le=1)
    seed: int | None = Field(None, ge=0)


class FineTuningJobCreate(BaseModel):
    """
    Schema for creating a new fine-tuning job.
    """
    base_model_name: str = Field(..., description="The name of the base model to use for fine-tuning")
    dataset_name: str = Field(..., description="The name of the dataset to use for fine-tuning")
    name: str = NameField(..., description="The name of the fine-tuning job")
    type: FineTuningJobType = Field(..., description="The type of fine-tuning job to run")
    provider: ComputeProvider = Field(ComputeProvider.GCP, description="The compute provider to use for fine-tuning")
    parameters: Dict[str, Any] = Field(..., description="The parameters for the fine-tuning job")


class FineTuningJobResponse(BaseModel):
    """
    Schema for fine-tuning job response data.
    """
    id: UUID = Field(..., description="The unique identifier of the fine-tuning job")
    created_at: DateTime = Field(..., description="The creation date and time of the fine-tuning job")
    updated_at: DateTime = Field(..., description="The last update date and time of the fine-tuning job")
    base_model_name: str = Field(..., description="The name of the base model used for fine-tuning")
    dataset_name: str = Field(..., description="The name of the dataset used for fine-tuning")
    status: FineTuningJobStatus = Field(..., description="The current status of the fine-tuning job")
    name: str = Field(..., description="The name of the fine-tuning job")
    type: FineTuningJobType = Field(..., description="The type of fine-tuning job")
    provider: ComputeProvider = Field(..., description="The compute provider used for fine-tuning")
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
    timestamps: Dict[str, Any] | None = Field(None, description="The timestamps recorded during the fine-tuning process")
    model_config = ConfigDict(from_attributes=True)
