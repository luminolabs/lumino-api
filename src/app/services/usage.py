from typing import Any
from uuid import UUID
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usage import Usage
from app.schemas.usage import UsageRecordResponse, UsageRecordCreate


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
        skip: int = 0,
        limit: int = 100
) -> list[UsageRecordResponse]:
    """Get a list of usage records for a given period."""
    result = await db.execute(
        select(Usage)
        .where(Usage.user_id == user_id)
        .where(func.date(Usage.created_at) >= start_date)
        .where(func.date(Usage.created_at) <= end_date)
        .order_by(Usage.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return [UsageRecordResponse.from_orm(record) for record in result.scalars().all()]


async def create_usage_record(db: AsyncSession, usage_record: UsageRecordCreate) -> UsageRecordResponse:
    """Create a new usage record."""
    db_usage_record = Usage(**usage_record.dict())
    db.add(db_usage_record)
    await db.commit()
    await db.refresh(db_usage_record)
    return UsageRecordResponse.from_orm(db_usage_record)


async def get_usage_by_service(
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date
) -> dict[Any, dict[str, float]]:
    """Get usage breakdown by service for a given period."""
    result = await db.execute(
        select(Usage.service_name, func.sum(Usage.usage_amount), func.sum(Usage.cost))
        .where(Usage.user_id == user_id)
        .where(func.date(Usage.created_at) >= start_date)
        .where(func.date(Usage.created_at) <= end_date)
        .group_by(Usage.service_name)
    )
    return {
        service_name: {"usage": float(usage), "cost": float(cost)}
        for service_name, usage, cost in result.all()
    }


async def get_daily_usage(
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date
) -> list[dict]:
    """Get daily usage for a given period."""
    result = await db.execute(
        select(
            func.date(Usage.created_at).label("date"),
            func.sum(Usage.usage_amount).label("usage"),
            func.sum(Usage.cost).label("cost")
        )
        .where(Usage.user_id == user_id)
        .where(func.date(Usage.created_at) >= start_date)
        .where(func.date(Usage.created_at) <= end_date)
        .group_by(func.date(Usage.created_at))
        .order_by(func.date(Usage.created_at))
    )
    return [
        {
            "date": date,
            "usage": float(usage),
            "cost": float(cost)
        }
        for date, usage, cost in result.all()
    ]