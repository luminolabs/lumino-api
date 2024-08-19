from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from uuid import UUID
from typing import Dict, Any

from app.constants import FineTuningJobStatus
from app.schemas.common import NAME_REGEX_LABEL


class FineTuningJobCreate(BaseModel):
    base_model_name: str
    dataset_name: str
    name: str = Field(
        ...,
        description=f"The name of the fine-tuning job. {NAME_REGEX_LABEL}",
        pattern="^[a-z0-9_-]+$",
        min_length=1,
        max_length=255
    )
    parameters: Dict[str, Any]


class FineTuningJobResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    base_model_name: str
    dataset_name: str
    status: FineTuningJobStatus
    name: str
    current_step: int | None
    total_steps: int | None
    current_epoch: int | None
    total_epochs: int | None
    num_tokens: int | None
    model_config = ConfigDict(from_attributes=True)


class FineTuningJobDetailResponse(FineTuningJobResponse):
    parameters: Dict[str, Any]
    metrics: Dict[str, Any] | None
