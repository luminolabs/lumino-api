from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.core.constants import BaseModelStatus


class BaseModelResponse(BaseModel):
    """
    Schema for base model response data.
    """
    id: UUID = Field(..., description="The unique identifier of the base model")
    description: str | None = Field(None, description="A description of the base model")
    hf_url: str = Field(..., description="The Hugging Face URL for the model")
    status: BaseModelStatus = Field(..., description="The current status of the base model")
    name: str = Field(..., description="The name of the base model")
    meta: Dict[str, Any] | None = Field(None, description="Additional metadata about the base model")
    model_config = ConfigDict(from_attributes=True)


class FineTunedModelResponse(BaseModel):
    """
    Schema for fine-tuned model response data.
    """
    id: UUID = Field(..., description="The unique identifier of the fine-tuned model")
    created_at: datetime = Field(..., description="The timestamp when the fine-tuned model was created")
    fine_tuning_job_name: str = Field(..., description="The name of the associated fine-tuning job")
    name: str = Field(..., description="The name of the fine-tuned model")
    artifacts: Dict[str, Any] | None = Field(None, description="Additional artifacts associated with the fine-tuned model")
    model_config = ConfigDict(from_attributes=True)
