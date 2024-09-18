from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.core.constants import UsageUnit, ServiceName


class CreditCommitRequest(BaseModel):
    """
    Schema for committing credits for a job.
    """
    user_id: UUID = Field(..., description="The ID of the user")
    usage_amount: int = Field(..., description="The amount of usage")
    usage_unit: UsageUnit = Field(..., description="The unit of usage", )
    service_name: ServiceName = Field(..., description="The name of the service")
    fine_tuning_job_id: UUID = Field(..., description="The ID of the job")


class CreditCommitResponse(BaseModel):
    """
    Schema for the response from committing credits for a job.
    """
    has_enough_credits: bool = Field(..., description="Whether the user has enough credits for the job")
    model_config = ConfigDict(from_attributes=True)


class CreditHistoryResponse(BaseModel):
    id: UUID = Field(..., description="The unique identifier for the credit record")
    created_at: datetime = Field(..., description="The timestamp when the credit record was created")
    credits: Decimal = Field(..., description="The amount of credits added or deducted")
    model_config = ConfigDict(from_attributes=True)