from typing import Dict, Union, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common import Pagination
from app.schemas.fine_tuning import FineTuningJobCreate, FineTuningJobResponse
from app.services.fine_tuning import (
    create_fine_tuning_job,
    get_fine_tuning_jobs,
    get_fine_tuning_job,
    cancel_fine_tuning_job,
    get_fine_tuning_job_logs,
)
from app.core.authentication import get_current_active_user
from app.schemas.user import UserResponse

router = APIRouter(tags=["Fine-tuning Jobs"])


@router.post("/fine-tuning", response_model=FineTuningJobResponse, status_code=status.HTTP_201_CREATED)
async def create_new_fine_tuning_job(
        job: FineTuningJobCreate,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobResponse:
    """
    Create a new fine-tuning job.
    """
    try:
        return await create_fine_tuning_job(db, current_user.id, job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/fine-tuning", response_model=Dict[str, Union[List[FineTuningJobResponse], Pagination]])
async def list_fine_tuning_jobs(
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[FineTuningJobResponse], Pagination]]:
    """
    List all fine-tuning jobs for the current user.
    """
    jobs, pagination = await get_fine_tuning_jobs(db, current_user.id, page, items_per_page)
    return {
        "data": jobs,
        "pagination": pagination
    }


@router.get("/fine-tuning/{job_name}", response_model=FineTuningJobResponse)
async def get_fine_tuning_job_details(
        job_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobResponse:
    """
    Get details of a specific fine-tuning job.
    """
    job = await get_fine_tuning_job(db, current_user.id, job_name)
    if not job:
        raise HTTPException(status_code=404, detail="Fine-tuning job not found")
    return job


@router.post("/fine-tuning/{job_name}/cancel", response_model=FineTuningJobResponse)
async def cancel_fine_tuning_job_request(
        job_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobResponse:
    """
    Cancel a fine-tuning job.
    """
    try:
        return await cancel_fine_tuning_job(db, current_user.id, job_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/fine-tuning/{job_name}/logs")
async def get_fine_tuning_job_logs_request(
        job_name: str,
        current_user: UserResponse = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> str:
    """
    Get logs of a fine-tuning job.
    """
    try:
        return await get_fine_tuning_job_logs(db, current_user.id, job_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
