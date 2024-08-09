from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Dict, Any


class FineTuningJobCreate(BaseModel):
    base_model_id: UUID
    dataset_id: UUID
    parameters: Dict[str, Any]


class FineTuningJobUpdate(BaseModel):
    parameters: Dict[str, Any] | None = None


class FineTuningJobResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    user_id: UUID
    base_model_id: UUID
    dataset_id: UUID
    status: str
    current_step: int | None
    total_steps: int | None
    current_epoch: int | None
    total_epochs: int | None
    num_tokens: int | None
    parameters: Dict[str, Any]
    metrics: Dict[str, Any] | None


class FineTuningJobDetailResponse(FineTuningJobResponse):
    fine_tuned_model_id: UUID | None
