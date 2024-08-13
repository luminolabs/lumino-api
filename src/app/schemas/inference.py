from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Dict, Any

from app.constants import InferenceEndpointStatus


class InferenceEndpointCreate(BaseModel):
    fine_tuned_model_name: str
    machine_type: str
    parameters: Dict[str, Any]
    name: str


class InferenceEndpointResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    fine_tuned_model_name: str
    status: InferenceEndpointStatus
    name: str
    machine_type: str
    parameters: Dict[str, Any]


class PromptRequest(BaseModel):
    prompt: str


class PromptResponse(BaseModel):
    id: UUID
    created_at: datetime
    inference_endpoint_name: str
    request: str
    response: str
    input_tokens: int
    output_tokens: int
    response_time: float
