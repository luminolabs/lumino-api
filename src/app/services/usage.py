from uuid import UUID
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usage import Usage
from app.schemas.common import Pagination
from app.schemas.usage import UsageRecordResponse


async def get_total_cost(db: AsyncSession, user_id: UUID, start_date: date, end_date: date) -> float:
    """Get total cost for a given period."""
    result = await db.execute(
        select(func.sum(Usage.cost))
        .where(Usage.user_id == user_id)
        .where(func.date(Usage.created_at) >= start_date)
        .where(func.date(Usage.created_at) <= end_date)
    )
    total_cost = result.scalar_one_or_none()
    return float(total_cost) if total_cost else 0.0


async def get_usage_records(
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[UsageRecordResponse], Pagination]:
    """Get a list of usage records for a given period with pagination."""
    total_count = await db.scalar(
        select(func.count())
        .select_from(Usage)
        .where(Usage.user_id == user_id)
        .where(func.date(Usage.created_at) >= start_date)
        .where(func.date(Usage.created_at) <= end_date)
    )

    total_pages = math.ceil(total_count / items_per_page)
    offset = (page - 1) * items_per_page

    result = await db.execute(
        select(Usage)
        .where(Usage.user_id == user_id)
        .where(func.date(Usage.created_at) >= start_date)
        .where(func.date(Usage.created_at) <= end_date)
        .order_by(Usage.created_at.desc())
        .offset(offset)
        .limit(items_per_page)
    )
    records = [UsageRecordResponse.from_orm(record) for record in result.scalars().all()]

    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None
    )

    return records, pagination
