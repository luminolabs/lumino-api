from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.schemas.fine_tuning import FineTuningJobCreate, FineTuningJobResponse, FineTuningJobUpdate, FineTuningJobDetailResponse
from app.core.fine_tuning import start_fine_tuning_job, cancel_fine_tuning_job_task, get_job_logs


async def create_fine_tuning_job(db: AsyncSession, user_id: UUID, job: FineTuningJobCreate) -> FineTuningJobResponse:
    """Create a new fine-tuning job."""
    db_job = FineTuningJob(
        user_id=user_id,
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


async def get_fine_tuning_jobs(db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100) -> list[FineTuningJobResponse]:
    """Get all fine-tuning jobs for a user."""
    result = await db.execute(
        select(FineTuningJob)
        .where(FineTuningJob.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return [FineTuningJobResponse.from_orm(job) for job in result.scalars().all()]


async def get_fine_tuning_job(db: AsyncSession, job_id: UUID) -> FineTuningJobDetailResponse | None:
    """Get a specific fine-tuning job."""
    result = await db.execute(
        select(FineTuningJob, FineTuningJobDetail)
        .join(FineTuningJobDetail)
        .where(FineTuningJob.id == job_id)
    )
    job, detail = result.first()
    if job:
        job_response = FineTuningJobDetailResponse.from_orm(job)
        job_response.parameters = detail.parameters
        job_response.metrics = detail.metrics
        return job_response
    return None


async def update_fine_tuning_job(db: AsyncSession, job_id: UUID, job_update: FineTuningJobUpdate) -> FineTuningJobResponse:
    """Update a fine-tuning job."""
    db_job = await db.get(FineTuningJob, job_id)
    if not db_job:
        raise ValueError("Fine-tuning job not found")

    update_data = job_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "parameters":
            db_job.details.parameters = value
        else:
            setattr(db_job, field, value)

    await db.commit()
    await db.refresh(db_job)
    return FineTuningJobResponse.from_orm(db_job)


async def cancel_fine_tuning_job(db: AsyncSession, job_id: UUID) -> FineTuningJobResponse:
    """Cancel a fine-tuning job."""
    db_job = await db.get(FineTuningJob, job_id)
    if not db_job:
        raise ValueError("Fine-tuning job not found")

    if db_job.status not in ["new", "pending", "running"]:
        raise ValueError("Job cannot be cancelled in its current state")

    db_job.status = "cancelled"
    await db.commit()
    await db.refresh(db_job)

    # Cancel the fine-tuning job task
    await cancel_fine_tuning_job_task(job_id)

    return FineTuningJobResponse.from_orm(db_job)


async def get_fine_tuning_job_logs(db: AsyncSession, job_id: UUID) -> str:
    """Get logs for a fine-tuning job."""
    db_job = await db.get(FineTuningJob, job_id)
    if not db_job:
        raise ValueError("Fine-tuning job not found")

    return await get_job_logs(job_id)
