import math
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.schemas.common import Pagination
from app.schemas.fine_tuning import FineTuningJobCreate, FineTuningJobResponse, FineTuningJobUpdate, FineTuningJobDetailResponse
from app.core.fine_tuning import start_fine_tuning_job, cancel_fine_tuning_job_task, get_job_logs


async def create_fine_tuning_job(db: AsyncSession, user_id: UUID, job: FineTuningJobCreate) -> FineTuningJobResponse:
    """Create a new fine-tuning job."""
    db_job = FineTuningJob(
        user_id=user_id,
        name=job.name,
        base_model_id=job.base_model_id,
        dataset_id=job.dataset_id,
        status="new"
    )
    db.add(db_job)
    await db.flush()

    db_job_detail = FineTuningJobDetail(
        fine_tuning_job_id=db_job.id,
        parameters=job.parameters
    )
    db.add(db_job_detail)
    await db.commit()
    await db.refresh(db_job)
    await db.refresh(db_job_detail)

    # Start the fine-tuning job asynchronously
    await start_fine_tuning_job(db_job.id)

    return FineTuningJobResponse.from_orm(db_job)


async def get_fine_tuning_jobs(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[FineTuningJobResponse], Pagination]:
    """Get all fine-tuning jobs for a user with pagination."""
    total_count = await db.scalar(
        select(func.count()).select_from(FineTuningJob).where(FineTuningJob.user_id == user_id)
    )

    total_pages = math.ceil(total_count / items_per_page)
    offset = (page - 1) * items_per_page

    result = await db.execute(
        select(FineTuningJob)
        .where(FineTuningJob.user_id == user_id)
        .offset(offset)
        .limit(items_per_page)
    )
    jobs = [FineTuningJobResponse.from_orm(job) for job in result.scalars().all()]

    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
        next_page=page + 1 if page < total_pages else None,
        previous_page=page - 1 if page > 1 else None
    )

    return jobs, pagination


async def get_fine_tuning_job(db: AsyncSession, user_id: UUID, job_name: str) -> FineTuningJobDetailResponse | None:
    """Get a specific fine-tuning job."""
    result = await db.execute(
        select(FineTuningJob, FineTuningJobDetail)
        .join(FineTuningJobDetail)
        .where(FineTuningJob.user_id == user_id, FineTuningJob.name == job_name)
    )
    job, detail = result.first()
    if job:
        job_response = FineTuningJobDetailResponse.from_orm(job)
        job_response.parameters = detail.parameters
        job_response.metrics = detail.metrics
        return job_response
    return None


async def cancel_fine_tuning_job(db: AsyncSession, user_id: UUID, job_name: str) -> FineTuningJobResponse:
    """Cancel a fine-tuning job."""
    result = await db.execute(
        select(FineTuningJob)
        .where(FineTuningJob.user_id == user_id, FineTuningJob.name == job_name)
    )
    db_job = result.scalar_one_or_none()
    if not db_job:
        raise ValueError("Fine-tuning job not found")

    if db_job.status not in ["new", "pending", "running"]:
        raise ValueError("Job cannot be cancelled in its current state")

    db_job.status = "cancelled"
    await db.commit()
    await db.refresh(db_job)

    # Cancel the fine-tuning job task
    await cancel_fine_tuning_job_task(db_job.id)

    return FineTuningJobResponse.from_orm(db_job)


async def get_fine_tuning_job_logs(db: AsyncSession, user_id: UUID, job_name: str) -> str:
    """Get logs for a fine-tuning job."""
    result = await db.execute(
        select(FineTuningJob)
        .where(FineTuningJob.user_id == user_id, FineTuningJob.name == job_name)
    )
    db_job = result.scalar_one_or_none()
    if not db_job:
        raise ValueError("Fine-tuning job not found")

    return await get_job_logs(db_job.id)
