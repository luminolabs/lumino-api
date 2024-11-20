from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import (
    FineTuningJobStatus,
    FineTuningJobType, FineTunedModelStatus, ComputeProvider
)
from app.core.exceptions import (
    BaseModelNotFoundError,
    DatasetNotFoundError,
    FineTuningJobAlreadyExistsError,
    ForbiddenError, FineTuningJobNotFoundError, BadRequestError
)
from app.core.scheduler_client import start_fine_tuning_job, stop_fine_tuning_job
from app.core.utils import setup_logger
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.models.user import User
from app.queries import datasets as dataset_queries
from app.queries import fine_tuned_models as ft_models_queries
from app.queries import fine_tuning as ft_queries
from app.queries import models as model_queries
from app.schemas.common import Pagination
from app.schemas.fine_tuning import (
    FineTuningJobCreate,
    FineTuningJobDetailResponse, FineTuningJobResponse
)

logger = setup_logger(__name__)

async def create_fine_tuning_job(
        db: AsyncSession,
        user: User,
        job: FineTuningJobCreate
) -> FineTuningJobDetailResponse:
    """Create a new fine-tuning job."""
    # Validate user status
    if not user.email_verified:
        raise ForbiddenError("Email verification required", logger)

    if user.credits_balance < config.fine_tuning_job_min_credits:
        raise ForbiddenError(f"Insufficient credits. Required: {config.fine_tuning_job_min_credits}", logger)

    # Validate base model
    base_model = await model_queries.get_base_model_by_name(db, job.base_model_name)
    if not base_model:
        raise BaseModelNotFoundError(f"Base model not found: {job.base_model_name}", logger)

    # Validate dataset
    dataset = await dataset_queries.get_dataset_by_name(db, user.id, job.dataset_name)
    if not dataset:
        raise DatasetNotFoundError(f"Dataset not found: {job.dataset_name}", logger)

    # Check for duplicate job name
    existing_job = await ft_queries.get_job_with_details(db, user.id, job.name)
    if existing_job:
        raise FineTuningJobAlreadyExistsError(f"Job name already exists: {job.name}", logger)

    try:
        # Prepare job parameters
        params = job.parameters.copy()
        params['use_lora'] = job.type in (FineTuningJobType.LORA, FineTuningJobType.QLORA)
        params['use_qlora'] = job.type == FineTuningJobType.QLORA

        # Create job record
        db_job = FineTuningJob(
            user_id=user.id,
            name=job.name,
            type=job.type,
            provider=job.provider,
            base_model_id=base_model.id,
            dataset_id=dataset.id,
            status=FineTuningJobStatus.NEW
        )
        db.add(db_job)
        await db.flush()

        # Create job details
        db_job_detail = FineTuningJobDetail(
            fine_tuning_job_id=db_job.id,
            parameters=params,
            metrics={},
            timestamps={
                "new": None, "queued": None, "running": None,
                "stopping": None, "stopped": None,
                "completed": None, "failed": None
            }
        )
        db.add(db_job_detail)
        await db.commit()
        await db.refresh(db_job)

        # Start the job via scheduler
        await start_fine_tuning_job(db_job.id)

        # Prepare response
        response_data = {
            **db_job.__dict__,
            'base_model_name': base_model.name,
            'dataset_name': dataset.name,
            'parameters': db_job_detail.parameters,
            'metrics': db_job_detail.metrics,
            'timestamps': db_job_detail.timestamps
        }

        logger.info(f"Created fine-tuning job: {db_job.id} for user: {user.id}")
        return FineTuningJobDetailResponse(**response_data)

    except Exception as e:
        await db.rollback()
        raise e

async def get_fine_tuning_jobs(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[FineTuningJobResponse], Pagination]:
    """Get all fine-tuning jobs for a user with pagination."""
    offset = (page - 1) * items_per_page

    # Get total count and paginated results
    total_count = await ft_queries.count_jobs(db, user_id)
    results = await ft_queries.list_jobs(db, user_id, offset, items_per_page)

    # Calculate pagination
    total_pages = (total_count + items_per_page - 1) // items_per_page
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
    )

    # Create response objects
    jobs = []
    for job, base_model_name, dataset_name in results:
        job_dict = job.__dict__
        job_dict['base_model_name'] = base_model_name
        job_dict['dataset_name'] = dataset_name
        jobs.append(FineTuningJobResponse(**job_dict))

    logger.info(f"Retrieved {len(jobs)} fine-tuning jobs for user: {user_id}, page: {page}")
    return jobs, pagination

# app/services/fine_tuning.py (continued)

async def get_fine_tuning_job(
        db: AsyncSession,
        user_id: UUID,
        job_name: str
) -> FineTuningJobDetailResponse:
    """Get detailed information about a specific fine-tuning job."""
    result = await ft_queries.get_job_with_details(db, user_id, job_name)
    if not result:
        raise FineTuningJobNotFoundError(f"Job not found: {job_name}", logger)

    job, detail, base_model_name, dataset_name = result
    response_data = {
        **job.__dict__,
        'base_model_name': base_model_name,
        'dataset_name': dataset_name,
        'parameters': detail.parameters,
        'metrics': detail.metrics,
        'timestamps': detail.timestamps
    }

    logger.info(f"Retrieved fine-tuning job: {job_name} for user: {user_id}")
    return FineTuningJobDetailResponse(**response_data)

async def cancel_fine_tuning_job(
        db: AsyncSession,
        user_id: UUID,
        job_name: str
) -> FineTuningJobDetailResponse:
    """Cancel a specific fine-tuning job."""
    # Get job details
    result = await ft_queries.get_job_with_details(db, user_id, job_name)
    if not result:
        raise FineTuningJobNotFoundError(f"Job not found: {job_name}", logger)

    job, detail, base_model_name, dataset_name = result

    # Validate job can be cancelled
    if job.provider == ComputeProvider.LUM:
        raise BadRequestError(f"Cannot cancel job running on {ComputeProvider.LUM} protocol", logger)

    if job.status != FineTuningJobStatus.RUNNING:
        raise BadRequestError(f"Job cannot be cancelled in state: {job.status.value}", logger)

    try:
        # Request job cancellation from scheduler
        await stop_fine_tuning_job(job.id, user_id)

        # Update job status
        job.status = FineTuningJobStatus.STOPPING
        await db.commit()
        await db.refresh(job)

        # Prepare response
        response_data = {
            **job.__dict__,
            'base_model_name': base_model_name,
            'dataset_name': dataset_name,
            'parameters': detail.parameters,
            'metrics': detail.metrics,
            'timestamps': detail.timestamps
        }

        logger.info(f"Cancelled fine-tuning job: {job_name} for user: {user_id}")
        return FineTuningJobDetailResponse(**response_data)

    except Exception as e:
        await db.rollback()
        raise e

async def delete_fine_tuning_job(
        db: AsyncSession,
        user_id: UUID,
        job_name: str
) -> None:
    """Mark a fine-tuning job and its associated model as deleted."""
    # Get job with fine-tuned model
    result = await ft_queries.get_job_with_details(db, user_id, job_name)
    if not result:
        raise FineTuningJobNotFoundError(f"Job not found: {job_name}", logger)

    job, detail, _, _ = result

    try:
        # Mark job as deleted
        job.status = FineTuningJobStatus.DELETED

        # If there's an associated fine-tuned model, mark it as deleted too
        fine_tuned_model = await ft_models_queries.get_existing_model(db, job.id, user_id)
        if fine_tuned_model:
            fine_tuned_model.status = FineTunedModelStatus.DELETED

        await db.commit()
        logger.info(f"Marked fine-tuning job as deleted: {job_name} for user: {user_id}")

    except Exception as e:
        await db.rollback()
        raise e

async def update_job_progress(
        db: AsyncSession,
        job: FineTuningJob,
        progress: dict
) -> bool:
    """Update job progress information."""

    # Ignore outdated progress updates
    if progress['current_step'] <= (job.current_step or -1):
        return True

    try:
        # Update job progress
        job.current_step = progress['current_step']
        job.total_steps = progress['total_steps']
        job.current_epoch = progress['current_epoch']
        job.total_epochs = progress['total_epochs']

        await db.commit()
        logger.info(f"Updated progress for job: {job.id}, step: {progress['current_step']}")
        return True

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update job progress: {str(e)}")
        return False

async def get_jobs_for_status_update(
        db: AsyncSession,
        include_recent_completed: bool = True
) -> List[FineTuningJob]:
    """Get jobs that need status updates."""
    non_terminal_statuses = [
        FineTuningJobStatus.NEW,
        FineTuningJobStatus.QUEUED,
        FineTuningJobStatus.RUNNING,
        FineTuningJobStatus.STOPPING
    ]

    completed_within_minutes = 10 if include_recent_completed else None

    jobs = await ft_queries.get_non_terminal_jobs(
        db,
        statuses=non_terminal_statuses,
        completed_within_minutes=completed_within_minutes
    )

    return jobs
