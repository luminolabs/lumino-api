from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Dict, Any


class BaseModelResponse(BaseModel):
    id: UUID
    description: str | None
    hf_url: str | None
    hf_is_gated: bool
    status: str
    metadata: Dict[str, Any] | None


class FineTunedModelResponse(BaseModel):
    id: UUID
    created_at: datetime
    user_id: UUID
    fine_tuning_job_id: UUID
    description: str | None
    artifacts: Dict[str, Any] | None


class FineTunedModelCreate(BaseModel):
    fine_tuning_job_id: UUID
    description: str | None = None


class FineTunedModelUpdate(BaseModel):
    description: str | None = None
