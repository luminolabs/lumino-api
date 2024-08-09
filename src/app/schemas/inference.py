from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Dict, Any


class InferenceEndpointCreate(BaseModel):
    fine_tuned_model_id: UUID
    machine_type: str
    parameters: Dict[str, Any]


class InferenceEndpointResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    user_id: UUID
    fine_tuned_model_id: UUID
    status: str
    machine_type: str
    parameters: Dict[str, Any]


class PromptRequest(BaseModel):
    prompt: str


class PromptResponse(BaseModel):
    id: UUID
    created_at: datetime
    inference_endpoint_id: UUID
    request: str
    response: str
    input_tokens: int
    output_tokens: int
    response_time: float


class InferenceEndpointUpdate(BaseModel):
    machine_type: str | None = None
    parameters: Dict[str, Any] | None = None
