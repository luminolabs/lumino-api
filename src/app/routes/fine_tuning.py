from typing import Dict, Union, List

from fastapi import APIRouter, Depends, status
from fastapi.params import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authentication import get_current_active_user
from app.core.database import get_db
from app.core.utils import setup_logger
from app.models.user import User
from app.schemas.common import Pagination
from app.schemas.fine_tuning import (
    FineTuningJobCreate,
    FineTuningJobResponse,
    FineTuningJobDetailResponse
)
from app.services.fine_tuning import (
    create_fine_tuning_job,
    get_fine_tuning_jobs,
    get_fine_tuning_job,
    cancel_fine_tuning_job,
    delete_fine_tuning_job
)

router = APIRouter(tags=["Fine-tuning Jobs"])
logger = setup_logger(__name__)

@router.post("/fine-tuning", response_model=FineTuningJobDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_new_fine_tuning_job(
        job: FineTuningJobCreate,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobDetailResponse:
    """Create a new fine-tuning job."""
    return await create_fine_tuning_job(db, current_user, job)

@router.get("/fine-tuning", response_model=Dict[str, Union[List[FineTuningJobResponse], Pagination]])
async def list_fine_tuning_jobs(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        items_per_page: int = Query(20, ge=1, le=100),
) -> Dict[str, Union[List[FineTuningJobResponse], Pagination]]:
    """List all fine-tuning jobs for the current user."""
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
    """Get details of a specific fine-tuning job."""
    return await get_fine_tuning_job(db, current_user.id, job_name)

@router.post("/fine-tuning/{job_name}/cancel", response_model=FineTuningJobDetailResponse)
async def cancel_fine_tuning_job_route(
        job_name: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> FineTuningJobDetailResponse:
    """Cancel a fine-tuning job."""
    return await cancel_fine_tuning_job(db, current_user.id, job_name)

@router.delete("/fine-tuning/{job_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fine_tuning_job_route(
        job_name: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a fine-tuning job."""
    await delete_fine_tuning_job(db, current_user.id, job_name)
