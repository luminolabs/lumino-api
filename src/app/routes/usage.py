from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.usage import TotalCostResponse, UsageRecordResponse
from app.services.usage import get_total_cost, get_usage_records
from app.services.user import get_current_user

router = APIRouter(tags=["Usage"])


@router.get("/usage/total-cost", response_model=TotalCostResponse)
async def get_total_cost_for_period(
        start_date: date = Query(..., description="Start date for the period"),
        end_date: date = Query(..., description="End date for the period"),
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> TotalCostResponse:
    """Get total cost for a given period."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    try:
        total_cost = await get_total_cost(db, current_user["id"], start_date, end_date)
        return TotalCostResponse(
            start_date=start_date,
            end_date=end_date,
            total_cost=total_cost
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/usage/records", response_model=list[UsageRecordResponse])
async def get_usage_records_for_period(
        start_date: date = Query(..., description="Start date for the period"),
        end_date: date = Query(..., description="End date for the period"),
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
) -> list[UsageRecordResponse]:
    """Get a list of usage records for a given period."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    try:
        return await get_usage_records(db, current_user["id"], start_date, end_date, skip, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
