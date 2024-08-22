from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import FineTuningJobStatus
from app.core.exceptions import (
    FineTuningJobNotFoundError,
    BaseModelNotFoundError,
    DatasetNotFoundError
)
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.models.base_model import BaseModel
from app.models.dataset import Dataset
from app.schemas.common import Pagination
from app.schemas.fine_tuning import FineTuningJobCreate, FineTuningJobResponse, FineTuningJobDetailResponse
from app.core.utils import setup_logger, paginate_query

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
        BaseModelNotFoundError: If the specified base model is not found.
        DatasetNotFoundError: If the specified dataset is not found.
    """
    # Check if base model exists
    base_model = await db.execute(select(BaseModel).where(BaseModel.name == job.base_model_name))
    base_model = base_model.scalar_one_or_none()
    if not base_model:
        raise BaseModelNotFoundError(f"Base model with name {job.base_model_name} not found, user: {user_id}", logger)

    # Check if dataset exists and belongs to the user
    dataset = await db.execute(select(Dataset).where(Dataset.name == job.dataset_name, Dataset.user_id == user_id))
    dataset = dataset.scalar_one_or_none()
    if not dataset:
        raise DatasetNotFoundError(f"Dataset with name {job.dataset_name} not found, user: {user_id}", logger)

    db_job = FineTuningJob(
        user_id=user_id,
        name=job.name,
        base_model_id=base_model.id,
        dataset_id=dataset.id,
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
    # TODO: Commented out since the scheduler client is not implemented yet
    # await start_fine_tuning_job(db_job.id)

    logger.info(f"Created fine-tuning job: {db_job.id} for user: {user_id}")
    return FineTuningJobResponse.from_orm(db_job)

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
    # Construct the query
    query = (
        select(FineTuningJob, BaseModel.name.label('base_model_name'), Dataset.name.label('dataset_name'))
        .join(BaseModel, FineTuningJob.base_model_id == BaseModel.id)
        .join(Dataset, FineTuningJob.dataset_id == Dataset.id)
        .where(FineTuningJob.user_id == user_id)
    )
    # Paginate the query
    jobs, pagination = await paginate_query(db, query, page, items_per_page)
    # Convert the results to response objects
    job_responses = []
    for job, base_model_name, dataset_name in jobs:
        job_dict = job.__dict__
        job_dict['base_model_name'] = base_model_name
        job_dict['dataset_name'] = dataset_name
        job_responses.append(FineTuningJobResponse(**job_dict))
    # Log the results and return them
    logger.info(f"Retrieved {len(job_responses)} fine-tuning jobs for user: {user_id}")
    return job_responses, pagination

async def get_fine_tuning_job(db: AsyncSession, user_id: UUID, job_name: str) -> FineTuningJobDetailResponse:
    """
    Get a specific fine-tuning job.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        job_name (str): The name of the fine-tuning job.

    Returns:
        FineTuningJobDetailResponse: The detailed information about the fine-tuning job.

    Raises:
        FineTuningJobNotFoundError: If the fine-tuning job is not found.
    """
    # Construct the query
    result = await db.execute(
        select(FineTuningJob, FineTuningJobDetail, BaseModel.name.label('base_model_name'), Dataset.name.label('dataset_name'))
        .join(FineTuningJobDetail)
        .join(BaseModel, FineTuningJob.base_model_id == BaseModel.id)
        .join(Dataset, FineTuningJob.dataset_id == Dataset.id)
        .where(FineTuningJob.user_id == user_id, FineTuningJob.name == job_name)
    )
    # Get the result and raise an error if not found
    row = result.first()
    if not row:
        raise FineTuningJobNotFoundError(f"Fine-tuning job not found: {job_name} for user: {user_id}", logger)

    # Convert the result to a response object
    job, detail, base_model_name, dataset_name = row
    job_dict = job.__dict__
    job_dict['base_model_name'] = base_model_name
    job_dict['dataset_name'] = dataset_name
    job_dict['parameters'] = detail.parameters
    job_dict['metrics'] = detail.metrics

    # Log the result and return it
    logger.info(f"Retrieved fine-tuning job: {job_name} for user: {user_id}")
    return FineTuningJobDetailResponse(**job_dict)

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
    """
    # Construct the query
    result = await db.execute(
        select(FineTuningJob)
        .where(FineTuningJob.user_id == user_id, FineTuningJob.name == job_name)
    )
    # Get the result and raise an error if not found
    db_job = result.scalar_one_or_none()
    if not db_job:
        raise FineTuningJobNotFoundError(f"Fine-tuning job not found: {job_name} for user: {user_id}", logger)

    # Update the job status and commit the changes
    db_job.status = FineTuningJobStatus.STOPPING
    await db.commit()
    await db.refresh(db_job)

    # Cancel the fine-tuning job task
    # TODO: Commented out since the scheduler client is not implemented yet
    # await cancel_fine_tuning_job_task(db_job.id)

    # Log the result and return it
    logger.info(f"Cancelled fine-tuning job: {job_name} for user: {user_id}")
    return FineTuningJobResponse.from_orm(db_job)

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
    # Construct the query
    result = await db.execute(
        select(FineTuningJob)
        .where(FineTuningJob.user_id == user_id, FineTuningJob.name == job_name)
    )

    # Get the result and raise an error if not found
    db_job = result.scalar_one_or_none()
    if not db_job:
        raise FineTuningJobNotFoundError(f"Fine-tuning job not found: {job_name} for user: {user_id}", logger)

    # Get the logs for the fine-tuning job
    # TODO: Commented out since the scheduler client is not implemented yet
    # logs = await get_job_logs(db_job.id)
    logs = "Logs not available yet"

    logger.info(f"Retrieved logs for fine-tuning job: {job_name}, user: {user_id}")
    return logs