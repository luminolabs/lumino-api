from datetime import date
from typing import Dict, Union, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import Pagination
from app.schemas.usage import TotalCostResponse, UsageRecordResponse
from app.services.usage import get_total_cost, get_usage_records
from app.core.authentication import get_current_active_user
from app.schemas.user import UserResponse

router = APIRouter(tags=["Usage"])


@router.get("/usage/total-cost", response_model=TotalCostResponse)
async def get_total_cost_for_period(
        start_date: date = Query(..., description="Start date for the period"),
        end_date: date = Query(..., description="End date for the period"),
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> TotalCostResponse:
    """Get total cost for a given period."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    try:
        total_cost = await get_total_cost(db, current_user.id, start_date, end_date)
        return TotalCostResponse(
            start_date=start_date,
            end_date=end_date,
            total_cost=total_cost
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=e.detail)


@router.get("/usage/records", response_model=Dict[str, Union[List[UsageRecordResponse], Pagination]])
async def list_usage_records(
        start_date: date = Query(...),
        end_date: date = Query(...),
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[UsageRecordResponse], Pagination]]:
    """Get a list of usage records for a given period."""
    records, pagination = await get_usage_records(db, current_user.id, start_date, end_date, page, items_per_page)
    return {
        "data": records,
        "pagination": pagination
    }
