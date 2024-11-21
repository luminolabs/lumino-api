from typing import Dict, Union, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import get_current_active_user
from app.core.database import get_db
from app.core.utils import setup_logger
from app.models.user import User
from app.schemas.common import Pagination
from app.schemas.usage import TotalCostResponse, UsageRecordResponse
from app.services.usage import get_total_cost, get_usage_records

router = APIRouter(tags=["Usage"])
logger = setup_logger(__name__)


@router.get("/usage/total-cost", response_model=TotalCostResponse)
async def get_total_cost_route(
        start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
        end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> TotalCostResponse:
    """Get total cost for a given period."""
    return await get_total_cost(db, current_user.id, start_date, end_date)


@router.get("/usage/records", response_model=Dict[str, Union[List[UsageRecordResponse], Pagination]])
async def list_usage_records(
        start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
        end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[UsageRecordResponse], Pagination]]:
    """Get a list of usage records for a given period."""
    records, pagination = await get_usage_records(
        db, current_user.id, start_date, end_date, page, items_per_page
    )
    return {
        "data": records,
        "pagination": pagination
    }
