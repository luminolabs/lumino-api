import math
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import FineTuningJobStatus
from app.core.exceptions import (
    FineTuningJobCreationError,
    FineTuningJobNotFoundError,
    FineTuningJobCancelError,
    BaseModelNotFoundError,
    DatasetNotFoundError
)
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.models.base_model import BaseModel
from app.models.dataset import Dataset
from app.schemas.common import Pagination
from app.schemas.fine_tuning import FineTuningJobCreate, FineTuningJobResponse, FineTuningJobDetailResponse
from app.core.scheduler_client import start_fine_tuning_job, cancel_fine_tuning_job_task, get_job_logs
from app.core.utils import setup_logger

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def create_fine_tuning_job(db: AsyncSession, user_id: UUID, job: FineTuningJobCreate) -> FineTuningJobResponse:
    """
    Create a new fine-tuning job.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user creating the job.
        job (FineTuningJobCreate): The fine-tuning job creation data.

    Returns:
        FineTuningJobResponse: The created fine-tuning job.

    Raises:
        FineTuningJobCreationError: If there's an error creating the fine-tuning job.
        BaseModelNotFoundError: If the specified base model is not found.
        DatasetNotFoundError: If the specified dataset is not found.
    """
    try:
        # Check if base model exists
        base_model = await db.get(BaseModel, job.base_model_id)
        if not base_model:
            raise BaseModelNotFoundError(f"Base model with ID {job.base_model_id} not found")

        # Check if dataset exists and belongs to the user
        dataset = await db.get(Dataset, job.dataset_id)
        if not dataset or dataset.user_id != user_id:
            raise DatasetNotFoundError(f"Dataset with ID {job.dataset_id} not found or does not belong to the user")

        db_job = FineTuningJob(
            user_id=user_id,
            name=job.name,
            base_model_id=job.base_model_id,
            dataset_id=job.dataset_id,
            status=FineTuningJobStatus.NEW
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

        logger.info(f"Created fine-tuning job: {db_job.id} for user: {user_id}")
        return FineTuningJobResponse.from_orm(db_job)
    except (BaseModelNotFoundError, DatasetNotFoundError) as e:
        logger.error(f"Error creating fine-tuning job for user {user_id}: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating fine-tuning job for user {user_id}: {e}")
        raise FineTuningJobCreationError(f"Failed to create fine-tuning job: {e}")


async def get_fine_tuning_jobs(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[FineTuningJobResponse], Pagination]:
    """
    Get all fine-tuning jobs for a user with pagination.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        tuple[list[FineTuningJobResponse], Pagination]: A tuple containing the list of fine-tuning jobs and pagination info.
    """
    try:
        # Count total items
        total_count = await db.scalar(
            select(func.count()).select_from(FineTuningJob).where(FineTuningJob.user_id == user_id)
        )

        # Calculate pagination
        total_pages = math.ceil(total_count / items_per_page)
        offset = (page - 1) * items_per_page

        # Fetch items
        result = await db.execute(
            select(FineTuningJob, BaseModel.name.label('base_model_name'), Dataset.name.label('dataset_name'))
            .join(BaseModel, FineTuningJob.base_model_id == BaseModel.id)
            .join(Dataset, FineTuningJob.dataset_id == Dataset.id)
            .where(FineTuningJob.user_id == user_id)
            .offset(offset)
            .limit(items_per_page)
        )

        jobs = []
        for row in result:
            job_dict = row.FineTuningJob.__dict__
            job_dict['base_model_name'] = row.base_model_name
            job_dict['dataset_name'] = row.dataset_name
            jobs.append(FineTuningJobResponse(**job_dict))

        # Create pagination object
        pagination = Pagination(
            total_pages=total_pages,
            current_page=page,
            items_per_page=items_per_page,
            next_page=page + 1 if page < total_pages else None,
            previous_page=page - 1 if page > 1 else None
        )

        logger.info(f"Retrieved {len(jobs)} fine-tuning jobs for user: {user_id}")
        return jobs, pagination
    except Exception as e:
        logger.error(f"Error retrieving fine-tuning jobs for user {user_id}: {e}")
        raise


async def get_fine_tuning_job(db: AsyncSession, user_id: UUID, job_name: str) -> FineTuningJobDetailResponse | None:
    """
    Get a specific fine-tuning job.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        job_name (str): The name of the fine-tuning job.

    Returns:
        FineTuningJobDetailResponse | None: The detailed information about the fine-tuning job, or None if not found.

    Raises:
        FineTuningJobNotFoundError: If the fine-tuning job is not found.
    """
    try:
        result = await db.execute(
            select(FineTuningJob, FineTuningJobDetail, BaseModel.name.label('base_model_name'), Dataset.name.label('dataset_name'))
            .join(FineTuningJobDetail)
            .join(BaseModel, FineTuningJob.base_model_id == BaseModel.id)
            .join(Dataset, FineTuningJob.dataset_id == Dataset.id)
            .where(FineTuningJob.user_id == user_id, FineTuningJob.name == job_name)
        )
        row = result.first()
        if row:
            job, detail, base_model_name, dataset_name = row
            job_dict = job.__dict__
            job_dict['base_model_name'] = base_model_name
            job_dict['dataset_name'] = dataset_name
            job_dict['parameters'] = detail.parameters
            job_dict['metrics'] = detail.metrics
            logger.info(f"Retrieved fine-tuning job: {job_name} for user: {user_id}")
            return FineTuningJobDetailResponse(**job_dict)
        logger.warning(f"Fine-tuning job not found: {job_name} for user: {user_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving fine-tuning job {job_name} for user {user_id}: {e}")
        raise FineTuningJobNotFoundError(f"Failed to retrieve fine-tuning job: {e}")


async def cancel_fine_tuning_job(db: AsyncSession, user_id: UUID, job_name: str) -> FineTuningJobResponse:
    """
    Cancel a fine-tuning job.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        job_name (str): The name of the fine-tuning job to cancel.

    Returns:
        FineTuningJobResponse: The updated fine-tuning job after cancellation.

    Raises:
        FineTuningJobNotFoundError: If the fine-tuning job is not found.
        FineTuningJobCancelError: If there's an error cancelling the fine-tuning job.
    """
    try:
        result = await db.execute(
            select(FineTuningJob)
            .where(FineTuningJob.user_id == user_id, FineTuningJob.name == job_name)
        )
        db_job = result.scalar_one_or_none()
        if not db_job:
            logger.warning(f"Fine-tuning job not found: {job_name} for user: {user_id}")
            raise FineTuningJobNotFoundError("Fine-tuning job not found")

        if db_job.status not in [FineTuningJobStatus.NEW, FineTuningJobStatus.PENDING, FineTuningJobStatus.RUNNING]:
            logger.warning(f"Cannot cancel fine-tuning job {job_name} in its current state: {db_job.status}")
            raise FineTuningJobCancelError("Job cannot be cancelled in its current state")

        db_job.status = FineTuningJobStatus.STOPPING
        await db.commit()
        await db.refresh(db_job)

        # Cancel the fine-tuning job task
        await cancel_fine_tuning_job_task(db_job.id)

        logger.info(f"Cancelled fine-tuning job: {job_name} for user: {user_id}")
        return FineTuningJobResponse.from_orm(db_job)
    except (FineTuningJobNotFoundError, FineTuningJobCancelError):
        raise
    except Exception as e:
        logger.error(f"Error cancelling fine-tuning job {job_name} for user {user_id}: {e}")
        raise FineTuningJobCancelError(f"Failed to cancel fine-tuning job: {e}")


async def get_fine_tuning_job_logs(db: AsyncSession, user_id: UUID, job_name: str) -> str:
    """
    Get logs for a fine-tuning job.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        job_name (str): The name of the fine-tuning job.

    Returns:
        str: The logs of the fine-tuning job.

    Raises:
        FineTuningJobNotFoundError: If the fine-tuning job is not found.
    """
    try:
        result = await db.execute(
            select(FineTuningJob)
            .where(FineTuningJob.user_id == user_id, FineTuningJob.name == job_name)
        )
        db_job = result.scalar_one_or_none()
        if not db_job:
            logger.warning(f"Fine-tuning job not found: {job_name} for user: {user_id}")
            raise FineTuningJobNotFoundError("Fine-tuning job not found")

        logs = await get_job_logs(db_job.id)
        logger.info(f"Retrieved logs for fine-tuning job: {job_name}, user: {user_id}")
        return logs
    except FineTuningJobNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving logs for fine-tuning job {job_name}, user {user_id}: {e}")
        raise FineTuningJobNotFoundError(f"Failed to retrieve logs: {e}")
