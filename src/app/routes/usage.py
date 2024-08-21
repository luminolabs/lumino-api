from typing import Dict, Union, List
from datetime import datetime, date

from fastapi import APIRouter, Depends
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.core.authentication import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.usage import TotalCostResponse, UsageRecordResponse
from app.schemas.common import Pagination
from app.services.usage import get_total_cost, get_usage_records
from app.utils import setup_logger
from app.core.exceptions import BadRequestError

# Set up API router
router = APIRouter(tags=["Usage"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


def parse_date(date_str: str) -> date:
    """
    Parse a date string in the format YYYY-MM-DD.

    Args:
        date_str (str): The date string to parse.
    Returns:
        date: The parsed date.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise BadRequestError(f"Invalid date format, use YYYY-MM-DD. Example: 2022-12-29; got: {date_str}")


@router.get("/usage/total-cost", response_model=TotalCostResponse)
async def get_total_cost_for_period(
        start_date: str = Query(..., description="Start date for the period (YYYY-MM-DD)"),
        end_date: str = Query(..., description="End date for the period (YYYY-MM-DD)"),
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> TotalCostResponse:
    """
    Get total cost for a given period.

    Args:
        start_date (str): Start date for the period (YYYY-MM-DD).
        end_date (str): End date for the period (YYYY-MM-DD).
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        TotalCostResponse: The total cost for the specified period.
    """
    # Parse dates
    start_date_obj = parse_date(start_date)
    end_date_obj = parse_date(end_date)
    # Get total cost
    total_cost = await get_total_cost(db, current_user.id, start_date_obj, end_date_obj)
    logger.info(f"Retrieved total cost for user: {current_user.id}, start_date: {start_date}, end_date: {end_date}")
    return total_cost


@router.get("/usage/records", response_model=Dict[str, Union[List[UsageRecordResponse], Pagination]])
async def list_usage_records(
        start_date: str = Query(..., description="Start date for the period (YYYY-MM-DD)"),
        end_date: str = Query(..., description="End date for the period (YYYY-MM-DD)"),
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[UsageRecordResponse], Pagination]]:
    """
    Get a list of usage records for a given period.

    Args:
        start_date (str): Start date for the period (YYYY-MM-DD).
        end_date (str): End date for the period (YYYY-MM-DD).
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        Dict[str, Union[List[UsageRecordResponse], Pagination]]: A dictionary containing the list of usage records and pagination info.
    """
    # Parse dates
    start_date_obj = parse_date(start_date)
    end_date_obj = parse_date(end_date)
    # Get usage records
    records, pagination = await get_usage_records(db, current_user.id, start_date_obj, end_date_obj, page, items_per_page)
    logger.info(f"Retrieved usage records for user: {current_user.id}, start_date: {start_date}, end_date: {end_date}, page: {page}")
    return {
        "data": records,
        "pagination": pagination
    }
