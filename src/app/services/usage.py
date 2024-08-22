from uuid import UUID
from datetime import date
import math
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_manager import config
from app.models.fine_tuning_job import FineTuningJob
from app.models.usage import Usage
from app.schemas.common import Pagination
from app.schemas.usage import UsageRecordResponse, TotalCostResponse
from app.utils import setup_logger, paginate_query
from app.core.exceptions import BadRequestError

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def get_total_cost(
        db: AsyncSession,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None
) -> TotalCostResponse:
    """
    Get total cost for a given period.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        start_date (date | None): The start date of the period (inclusive).
        end_date (date | None): The end date of the period (inclusive).

    Returns:
        TotalCostResponse: The total cost for the specified period.

    Raises:
        BadRequestError: If the end date is before the start date.
    """
    # Validate dates
    if start_date and end_date and end_date < start_date:
        raise BadRequestError(f"End date must be after start date; start_date: {start_date}, end_date: {end_date}")

    # Construct query
    query = select(func.sum(Usage.cost)).where(Usage.user_id == user_id)
    if start_date:
        query = query.where(func.date(Usage.created_at) >= start_date)
    if end_date:
        query = query.where(func.date(Usage.created_at) <= end_date)

    # Execute query
    result = await db.execute(query)
    total_cost = result.scalar_one_or_none()

    logger.info(f"Retrieved total cost for user: {user_id}, start_date: {start_date}, end_date: {end_date}")
    return TotalCostResponse(
        start_date=start_date,
        end_date=end_date,
        total_cost=float(total_cost) if total_cost else 0.0
    )


async def get_usage_records(
        db: AsyncSession,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[UsageRecordResponse], Pagination]:
    """
    Get a list of usage records for a given period with pagination.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        start_date (date | None): The start date of the period (inclusive).
        end_date (date | None): The end date of the period (inclusive).
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        tuple[list[UsageRecordResponse], Pagination]: A tuple containing the list of usage records and pagination info.

    Raises:
        BadRequestError: If the end date is before the start date.
    """
    # Validate dates
    if start_date and end_date and end_date < start_date:
        raise BadRequestError(f"End date must be after start date; start_date: {start_date}, end_date: {end_date}")
    # Construct query
    query = (
        select(Usage, FineTuningJob.name.label('fine_tuning_job_name'))
        .join(FineTuningJob, Usage.fine_tuning_job_id == FineTuningJob.id)
        .where(Usage.user_id == user_id)
    )
    if start_date:
        query = query.where(func.date(Usage.created_at) >= start_date)
    if end_date:
        query = query.where(func.date(Usage.created_at) <= end_date)
    # Paginate query
    results, pagination = await paginate_query(db, query.order_by(Usage.created_at.desc()), page, items_per_page)
    records = []
    # Create response objects
    for row in results:
        usage_dict = row.Usage.__dict__
        usage_dict['fine_tuning_job_name'] = row.fine_tuning_job_name
        records.append(UsageRecordResponse(**usage_dict))
    # Log and return records
    logger.info(f"Retrieved {len(records)} usage records for user: {user_id}, page: {page}")
    return records, pagination