from typing import Dict, Union, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.authentication import get_current_active_user
from app.core.exceptions import (
    BadRequestError,
    NotFoundError,
    FineTuningJobCreationError,
    FineTuningJobNotFoundError,
    FineTuningJobCancelError
)
from app.core.database import get_db
from app.schemas.common import Pagination
from app.schemas.fine_tuning import FineTuningJobCreate, FineTuningJobResponse, FineTuningJobDetailResponse
from app.schemas.user import UserResponse
from app.services.fine_tuning import (
    create_fine_tuning_job,
    get_fine_tuning_jobs,
    get_fine_tuning_job,
    cancel_fine_tuning_job,
    get_fine_tuning_job_logs,
)
from app.core.utils import setup_logger

router = APIRouter(tags=["Fine-tuning Jobs"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.post("/fine-tuning", response_model=FineTuningJobResponse, status_code=status.HTTP_201_CREATED)
async def create_new_fine_tuning_job(
        job: FineTuningJobCreate,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobResponse:
    """
    Create a new fine-tuning job.

    Args:
        job (FineTuningJobCreate): The fine-tuning job creation data.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        FineTuningJobResponse: The created fine-tuning job.

    Raises:
        FineTuningJobCreationError: If there's an error creating the fine-tuning job.
    """
    try:
        logger.info(f"Creating new fine-tuning job for user: {current_user.id}")
        new_job = await create_fine_tuning_job(db, current_user.id, job)
        logger.info(f"Successfully created fine-tuning job: {new_job.id} for user: {current_user.id}")
        return new_job
    except FineTuningJobCreationError as e:
        logger.error(f"Error creating fine-tuning job for user {current_user.id}: {e.detail}")
        raise BadRequestError(e.detail)


@router.get("/fine-tuning", response_model=Dict[str, Union[List[FineTuningJobResponse], Pagination]])
async def list_fine_tuning_jobs(
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[FineTuningJobResponse], Pagination]]:
    """
    List all fine-tuning jobs for the current user.

    Args:
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        Dict[str, Union[List[FineTuningJobResponse], Pagination]]: A dictionary containing the list of fine-tuning jobs and pagination info.
    """
    logger.info(f"Fetching fine-tuning jobs for user: {current_user.id}")
    jobs, pagination = await get_fine_tuning_jobs(db, current_user.id, page, items_per_page)
    return {
        "data": jobs,
        "pagination": pagination
    }


@router.get("/fine-tuning/{job_name}", response_model=FineTuningJobDetailResponse)
async def get_fine_tuning_job_details(
        job_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobDetailResponse:
    """
    Get details of a specific fine-tuning job.

    Args:
        job_name (str): The name of the fine-tuning job.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        FineTuningJobDetailResponse: The detailed information about the fine-tuning job.

    Raises:
        FineTuningJobNotFoundError: If the fine-tuning job is not found.
    """
    logger.info(f"Fetching fine-tuning job details for user: {current_user.id}, job name: {job_name}")
    job = await get_fine_tuning_job(db, current_user.id, job_name)
    if not job:
        logger.warning(f"Fine-tuning job not found for user: {current_user.id}, job name: {job_name}")
        raise FineTuningJobNotFoundError("Fine-tuning job not found")
    return job


@router.post("/fine-tuning/{job_name}/cancel", response_model=FineTuningJobResponse)
async def cancel_fine_tuning_job_request(
        job_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobResponse:
    """
    Cancel a fine-tuning job.

    Args:
        job_name (str): The name of the fine-tuning job to cancel.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        FineTuningJobResponse: The updated fine-tuning job after cancellation.

    Raises:
        FineTuningJobNotFoundError: If the fine-tuning job is not found.
        FineTuningJobCancelError: If there's an error cancelling the fine-tuning job.
    """
    try:
        logger.info(f"Cancelling fine-tuning job for user: {current_user.id}, job name: {job_name}")
        cancelled_job = await cancel_fine_tuning_job(db, current_user.id, job_name)
        logger.info(f"Successfully cancelled fine-tuning job: {job_name} for user: {current_user.id}")
        return cancelled_job
    except FineTuningJobNotFoundError as e:
        logger.error(f"Fine-tuning job not found for user {current_user.id}, job name {job_name}: {e.detail}")
        raise NotFoundError(e.detail)
    except FineTuningJobCancelError as e:
        logger.error(f"Error cancelling fine-tuning job for user {current_user.id}, job name {job_name}: {e.detail}")
        raise BadRequestError(e.detail)


@router.get("/fine-tuning/{job_name}/logs")
async def get_fine_tuning_job_logs_request(
        job_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> str:
    """
    Get logs of a fine-tuning job.

    Args:
        job_name (str): The name of the fine-tuning job.
        current_user (UserResponse): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        str: The logs of the fine-tuning job.

    Raises:
        FineTuningJobNotFoundError: If the fine-tuning job is not found.
        BadRequestError: If there's an error retrieving the logs.
    """
    try:
        logger.info(f"Fetching logs for fine-tuning job: {job_name}, user: {current_user.id}")
        logs = await get_fine_tuning_job_logs(db, current_user.id, job_name)
        logger.info(f"Successfully retrieved logs for fine-tuning job: {job_name}, user: {current_user.id}")
        return logs
    except FineTuningJobNotFoundError as e:
        logger.error(f"Fine-tuning job not found for user {current_user.id}, job name {job_name}: {e.detail}")
        raise NotFoundError(e.detail)
    except Exception as e:
        logger.error(f"Error retrieving logs for fine-tuning job {job_name}, user {current_user.id}: {e}")
        raise BadRequestError(f"Failed to retrieve logs: {e}")