from typing import Dict, Union, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import get_current_active_user
from app.core.config_manager import config
from app.core.database import get_db
from app.core.utils import setup_logger
from app.models.user import User
from app.schemas.common import Pagination
from app.schemas.fine_tuning import FineTuningJobCreate, FineTuningJobResponse, FineTuningJobDetailResponse
from app.services.fine_tuning import (
    create_fine_tuning_job,
    get_fine_tuning_jobs,
    get_fine_tuning_job, cancel_fine_tuning_job,
)

# Set up API router
router = APIRouter(tags=["Fine-tuning Jobs"])

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


@router.post("/fine-tuning", response_model=FineTuningJobDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_new_fine_tuning_job(
        job: FineTuningJobCreate,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobDetailResponse:
    """
    Create a new fine-tuning job.

    Args:
        job (FineTuningJobCreate): The fine-tuning job creation data.
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        FineTuningJobDetailResponse: The created fine-tuning job.
    """
    return await create_fine_tuning_job(db, current_user, job)


@router.get("/fine-tuning", response_model=Dict[str, Union[List[FineTuningJobResponse], Pagination]])
async def list_fine_tuning_jobs(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[FineTuningJobResponse], Pagination]]:
    """
    List all fine-tuning jobs for the current user.

    Args:
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        Dict[str, Union[List[FineTuningJobResponse], Pagination]]: A dictionary containing the list of fine-tuning jobs and pagination info.
    """
    jobs, pagination = await get_fine_tuning_jobs(db, current_user.id, page, items_per_page)
    return {
        "data": jobs,
        "pagination": pagination
    }


@router.get("/fine-tuning/{job_name}", response_model=FineTuningJobDetailResponse)
async def get_fine_tuning_job_details(
        job_name: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobDetailResponse:
    """
    Get details of a specific fine-tuning job.

    Args:
        job_name (str): The name of the fine-tuning job.
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        FineTuningJobDetailResponse: The detailed information about the fine-tuning job.
    """
    job = await get_fine_tuning_job(db, current_user.id, job_name)
    return job


@router.post("/fine-tuning/{job_name}/cancel", response_model=FineTuningJobDetailResponse)
async def cancel_fine_tuning_job_request(
        job_name: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobDetailResponse:
    """
    Cancel a fine-tuning job.

    Args:
        job_name (str): The name of the fine-tuning job to cancel.
        current_user (User): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        FineTuningJobDetailResponse: The updated fine-tuning job information.
    """
    cancelled_job = await cancel_fine_tuning_job(db, current_user.id, job_name)
    return cancelled_job


@router.get("/fine-tuning/{job_name}/logs", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def get_fine_tuning_job_logs_request() -> str:
    return "Not implemented"
