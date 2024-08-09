from pydantic import BaseModel
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal


class UsageRecordResponse(BaseModel):
    id: UUID
    created_at: datetime
    user_id: UUID
    service_name: str
    service_id: UUID
    usage_amount: Decimal
    cost: Decimal


class TotalCostResponse(BaseModel):
    start_date: date
    end_date: date
    total_cost: Decimal


class UsageRecordCreate(BaseModel):
    user_id: UUID
    service_name: str
    service_id: UUID
    usage_amount: Decimal
    cost: Decimal


class UsageRecordUpdate(BaseModel):
    usage_amount: Decimal | None = None
    cost: Decimal | None = None
