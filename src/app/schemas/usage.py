from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.core.constants import UsageUnit, ServiceName
from app.schemas.common import DateTime


class UsageRecordResponse(BaseModel):
    """
    Schema for usage record response data.
    """
    id: UUID = Field(..., description="The unique identifier of the usage record")
    created_at: DateTime = Field(..., description="The timestamp when the usage record was created")
    service_name: ServiceName = Field(..., description="The name of the service used")
    usage_amount: float = Field(..., description="The amount of usage for the service")
    usage_unit: UsageUnit = Field(..., description="The unit of usage for the service")
    cost: float = Field(..., description="The cost associated with the usage")
    fine_tuning_job_name: str = Field(..., description="The name of the associated fine-tuning job")
    model_config = ConfigDict(from_attributes=True)


class TotalCostResponse(BaseModel):
    """
    Schema for total cost response data.
    """
    start_date: date = Field(..., description="The start date of the period for which the cost is calculated")
    end_date: date = Field(..., description="The end date of the period for which the cost is calculated")
    total_cost: float = Field(..., description="The total cost for the specified period")
    model_config = ConfigDict(from_attributes=True)
