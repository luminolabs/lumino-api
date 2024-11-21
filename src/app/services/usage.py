from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.core.utils import setup_logger
from app.queries import usage as usage_queries
from app.schemas.common import Pagination
from app.schemas.usage import UsageRecordResponse, TotalCostResponse

logger = setup_logger(__name__)


async def get_usage_records(
        db: AsyncSession,
        user_id: UUID,
        start_date_str: str,
        end_date_str: str,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[UsageRecordResponse], Pagination]:
    """
    Get usage records for a user with pagination.

    Args:
        db: Database session
        user_id: User ID
        start_date_str: Start date in YYYY-MM-DD format
        end_date_str: End date in YYYY-MM-DD format
        page: Page number
        items_per_page: Items per page

    Returns:
        Tuple of usage records and pagination info

    Raises:
        BadRequestError: If dates are invalid
    """
    # Parse and validate dates
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise BadRequestError(
            "Invalid date format. Please use YYYY-MM-DD format"
        )

    if end_date < start_date:
        raise BadRequestError(
            f"End date ({end_date}) must be after start date ({start_date})"
        )

    # Calculate pagination
    offset = (page - 1) * items_per_page

    # Get total count and records
    total_count = await usage_queries.count_usage_records(
        db, user_id, start_date, end_date
    )

    usage_records = await usage_queries.get_usage_records(
        db, user_id, start_date, end_date, offset, items_per_page
    )

    # Prepare pagination
    total_pages = (total_count + items_per_page - 1) // items_per_page
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page
    )

    # Create response objects
    usage_responses = []
    for usage, job_name in usage_records:
        usage_dict = usage.__dict__
        usage_dict['fine_tuning_job_name'] = job_name
        usage_responses.append(UsageRecordResponse(**usage_dict))

    logger.info(
        f"Retrieved {len(usage_responses)} usage records for user: {user_id} "
        f"between {start_date} and {end_date}"
    )

    return usage_responses, pagination


async def get_total_cost(
        db: AsyncSession,
        user_id: UUID,
        start_date_str: str,
        end_date_str: str
) -> TotalCostResponse:
    """
    Get total cost for a period.

    Args:
        db: Database session
        user_id: User ID
        start_date_str: Start date in YYYY-MM-DD format
        end_date_str: End date in YYYY-MM-DD format

    Returns:
        Total cost information

    Raises:
        BadRequestError: If dates are invalid
    """
    # Parse and validate dates
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        raise BadRequestError(
            "Invalid date format. Please use YYYY-MM-DD format"
        )

    if end_date < start_date:
        raise BadRequestError(
            f"End date ({end_date}) must be after start date ({start_date})"
        )

    # Get total cost
    total_cost = await usage_queries.get_total_cost(
        db, user_id, start_date, end_date
    )

    logger.info(
        f"Calculated total cost for user {user_id}: {total_cost} "
        f"between {start_date} and {end_date}"
    )

    return TotalCostResponse(
        start_date=start_date,
        end_date=end_date,
        total_cost=total_cost
    )
