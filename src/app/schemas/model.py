from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Dict, Any

from app.constants import BaseModelStatus


class BaseModelResponse(BaseModel):
    """
    Schema for base model response data.

    Attributes:
        id (UUID): The unique identifier of the base model.
        description (str): A description of the base model.
        hf_url (str): The Hugging Face URL for the model.
        hf_is_gated (bool): Whether the model is gated on Hugging Face.
        status (BaseModelStatus): The current status of the base model.
        name (str): The name of the base model.
        meta (Dict[str, Any] | None): Additional metadata about the base model.
    """
    id: UUID
    description: str
    hf_url: str
    hf_is_gated: bool
    status: BaseModelStatus
    name: str
    meta: Dict[str, Any] | None
    model_config = ConfigDict(from_attributes=True)


class FineTunedModelResponse(BaseModel):
    """
    Schema for fine-tuned model response data.

    Attributes:
        id (UUID): The unique identifier of the fine-tuned model.
        created_at (datetime): The timestamp when the fine-tuned model was created.
        fine_tuning_job_name (str): The name of the associated fine-tuning job.
        name (str): The name of the fine-tuned model.
        description (str | None): A description of the fine-tuned model.
        artifacts (Dict[str, Any] | None): Additional artifacts associated with the fine-tuned model.
    """
    id: UUID
    created_at: datetime
    fine_tuning_job_name: str
    name: str
    description: str | None
    artifacts: Dict[str, Any] | None
    model_config = ConfigDict(from_attributes=True)