from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.fine_tuning import FineTuningJobCreate, FineTuningJobResponse, FineTuningJobUpdate
from app.services.fine_tuning import (
    create_fine_tuning_job,
    get_fine_tuning_jobs,
    get_fine_tuning_job,
    cancel_fine_tuning_job,
    get_fine_tuning_job_logs,
)
from app.services.user import get_current_user

router = APIRouter(tags=["Fine-tuning Jobs"])


@router.post("/fine-tuning", response_model=FineTuningJobResponse, status_code=status.HTTP_201_CREATED)
async def create_new_fine_tuning_job(
        job: FineTuningJobCreate,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobResponse:
    """
    Create a new fine-tuning job.

    Args:
        job (FineTuningJobCreate): The fine-tuning job data for creation.
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        FineTuningJobResponse: The created fine-tuning job's data.

    Raises:
        HTTPException: If there's an error creating the fine-tuning job.
    """
    try:
        return await create_fine_tuning_job(db, current_user["id"], job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/fine-tuning", response_model=list[FineTuningJobResponse])
async def list_fine_tuning_jobs(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        skip: int = 0,
        limit: int = 100,
) -> list[FineTuningJobResponse]:
    """
    List all fine-tuning jobs.

    Args:
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.
        skip (int): The number of items to skip (for pagination).
        limit (int): The maximum number of items to return (for pagination).

    Returns:
        list[FineTuningJobResponse]: A list of fine-tuning jobs belonging to the current user.
    """
    return await get_fine_tuning_jobs(db, current_user["id"], skip, limit)


@router.get("/fine-tuning/{job_id}", response_model=FineTuningJobResponse)
async def get_fine_tuning_job_details(
        job_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobResponse:
    """
    Get details of a specific fine-tuning job.

    Args:
        job_id (UUID): The ID of the fine-tuning job to retrieve.
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        FineTuningJobResponse: The requested fine-tuning job's data.

    Raises:
        HTTPException: If the fine-tuning job is not found or doesn't belong to the current user.
    """
    job = await get_fine_tuning_job(db, job_id)
    if not job or job.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Fine-tuning job not found")
    return job


@router.post("/fine-tuning/{job_id}/cancel", response_model=FineTuningJobResponse)
async def cancel_fine_tuning_job_request(
        job_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobResponse:
    """
    Cancel a fine-tuning job.

    Args:
        job_id (UUID): The ID of the fine-tuning job to cancel.
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        FineTuningJobResponse: The updated fine-tuning job's data.

    Raises:
        HTTPException: If the fine-tuning job is not found, doesn't belong to the current user, or if there's an error cancelling it.
    """
    job = await get_fine_tuning_job(db, job_id)
    if not job or job.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Fine-tuning job not found")
    try:
        return await cancel_fine_tuning_job(db, job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/fine-tuning/{job_id}/logs")
async def get_fine_tuning_job_logs_request(
        job_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
) -> str:
    """
    Get logs of a fine-tuning job.

    Args:
        job_id (UUID): The ID of the fine-tuning job to retrieve logs for.
        current_user (dict): The current authenticated user.
        db (AsyncSession): The database session.

    Returns:
        str: The logs of the fine-tuning job.

    Raises:
        HTTPException: If the fine-tuning job is not found or doesn't belong to the current user.
    """
    job = await get_fine_tuning_job(db, job_id)
    if not job or job.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="Fine-tuning job not found")
    try:
        return await get_fine_tuning_job_logs(db, job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
