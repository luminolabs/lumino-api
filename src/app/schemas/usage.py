from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal


class UsageRecordResponse(BaseModel):
    id: UUID
    created_at: datetime
    service_name: str
    usage_amount: Decimal
    cost: Decimal
    fine_tuning_job_name: str
    inference_endpoint_name: str


class TotalCostResponse(BaseModel):
    start_date: date
    end_date: date
    total_cost: Decimal
