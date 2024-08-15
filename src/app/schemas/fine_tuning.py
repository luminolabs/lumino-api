from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Dict, Any

from app.constants import FineTuningJobStatus


class FineTuningJobCreate(BaseModel):
    base_model_name: str
    dataset_name: str
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
