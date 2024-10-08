from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.core.constants import UsageUnit, ServiceName, BillingTransactionType
from app.schemas.common import DateTime


class CreditDeductRequest(BaseModel):
    """
    Schema for committing credits for a job.
    """
    user_id: UUID = Field(..., description="The ID of the user")
    usage_amount: int = Field(..., description="The amount of usage")
    usage_unit: UsageUnit = Field(..., description="The unit of usage")
    service_name: ServiceName = Field(..., description="The name of the service")
    fine_tuning_job_id: UUID = Field(..., description="The ID of the job")

class CreditAddRequest(BaseModel):
    """
    Schema for adding credits to a user's account.
    """
    user_id: UUID = Field(..., description="The ID of the user")
    amount: float = Field(..., description="The amount of credits to add")
    transaction_id: str = Field(..., description="The transaction ID")

class CreditHistoryResponse(BaseModel):
    id: UUID = Field(..., description="The unique identifier for the credit record")
    created_at: DateTime = Field(..., description="The timestamp when the credit record was created")
    credits: float = Field(..., description="The amount of credits added or deducted")
    transaction_id: str = Field(..., description="The transaction ID")
    transaction_type: BillingTransactionType = Field(..., description="The type of transaction")
    model_config = ConfigDict(from_attributes=True)