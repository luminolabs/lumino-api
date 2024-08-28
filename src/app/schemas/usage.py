from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal


class UsageRecordResponse(BaseModel):
    """
    Schema for usage record response data.
    """
    id: UUID = Field(..., description="The unique identifier of the usage record")
    created_at: datetime = Field(..., description="The timestamp when the usage record was created")
    service_name: str = Field(..., description="The name of the service used")
    usage_amount: float = Field(..., description="The amount of usage for the service")
    cost: float = Field(..., description="The cost associated with the usage")
    fine_tuning_job_name: str = Field(..., description="The name of the associated fine-tuning job")
    model_config = ConfigDict(from_attributes=True)


class TotalCostResponse(BaseModel):
    """
    Schema for total cost response data.
    """
    start_date: date = Field(..., description="The start date of the period for which the cost is calculated")
    end_date: date = Field(..., description="The end date of the period for which the cost is calculated")
    total_cost: Decimal = Field(..., description="The total cost for the specified period")
    model_config = ConfigDict(from_attributes=True)
