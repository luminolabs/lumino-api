from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Dict, Any


class BaseModelResponse(BaseModel):
    id: UUID
    description: str
    hf_url: str
    hf_is_gated: bool
    status: str
    name: str
    meta: Dict[str, Any] | None


class FineTunedModelResponse(BaseModel):
    id: UUID
    created_at: datetime
    fine_tuning_job_name: str
    name: str
    description: str | None
    artifacts: Dict[str, Any] | None
