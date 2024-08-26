from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import FineTuningJobStatus
from app.core.exceptions import (
    FineTuningJobNotFoundError,
    BaseModelNotFoundError,
    DatasetNotFoundError, FineTuningJobAlreadyExistsError, BadRequestError
)
from app.core.scheduler_client import start_fine_tuning_job, stop_fine_tuning_job
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

    # Check if the job name is unique for the user
    existing_job = await db.execute(select(FineTuningJob).where(FineTuningJob.user_id == user_id, FineTuningJob.name == job.name))
    existing_job = existing_job.scalar_one_or_none()
    if existing_job:
        raise FineTuningJobAlreadyExistsError(f"Fine-tuning job with name {job.name} already exists for user: {user_id}", logger)

    # Create the main fine-tuning job record
    db_job = FineTuningJob(
        user_id=user_id,
        name=job.name,
        base_model_id=base_model.id,
        dataset_id=dataset.id,
        status=FineTuningJobStatus.NEW
    )
    # Create the job details record
    db_job_detail = FineTuningJobDetail(
        fine_tuning_job_id=db_job.id,
        parameters=job.parameters
    )
    # Add the records to the database and commit the changes
    db.add(db_job)
    await db.flush()  # Ensure the job ID is generated before adding the detail record
    db_job_detail.fine_tuning_job_id = db_job.id
    db.add(db_job_detail)
    await db.commit()

    # Start the fine-tuning job
    await start_fine_tuning_job(db_job.id)

    # Prepare the response
    db_job_dict = db_job.__dict__
    db_job_dict['base_model_name'] = db_job.base_model.name
    db_job_dict['dataset_name'] = db_job.dataset.name

    logger.info(f"Created fine-tuning job: {db_job.id} for user: {user_id}")
    return FineTuningJobResponse(**db_job_dict)


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


async def cancel_fine_tuning_job(db: AsyncSession, user_id: UUID, job_name: str) -> FineTuningJobDetailResponse:
    """
    Cancel a specific fine-tuning job.

    Args:
        db (AsyncSession): The database session.
        user_id (UUID): The ID of the user.
        job_name (str): The name of the fine-tuning job.

    Returns:
        FineTuningJobDetailResponse: The updated fine-tuning job information.

    Raises:
        FineTuningJobNotFoundError: If the fine-tuning job is not found.
        FineTuningJobCancellationError: If there's an error cancelling the job.
    """
    # Get the job from the database
    job = await get_fine_tuning_job(db, user_id, job_name)

    # Check if the job is in a state that can be cancelled
    if job.status != FineTuningJobStatus.RUNNING:
        raise BadRequestError(f"Job {job_name} cannot be cancelled in its current state: {job.status.value}", logger)

    # Request job cancellation from the scheduler
    await stop_fine_tuning_job(job.id)

    # Update the job status in our database
    db_job = await db.get(FineTuningJob, job.id)
    db_job.status = FineTuningJobStatus.STOPPING
    await db.commit()
    await db.refresh(db_job)

    logger.info(f"Stopping fine-tuning job: {job_name} for user: {user_id}")
    return await get_fine_tuning_job(db, user_id, job_name)