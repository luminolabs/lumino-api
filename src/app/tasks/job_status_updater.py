from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FineTuningJobStatus
from app.core.database import AsyncSessionLocal
from app.core.scheduler_client import fetch_job_details
from app.core.utils import setup_logger
from app.queries import fine_tuning as ft_queries
from app.services.fine_tuned_model import create_fine_tuned_model
from app.services.fine_tuning import update_job_progress

logger = setup_logger(__name__)

# Map scheduler statuses to our internal statuses
STATUS_MAPPING = {
    "WAIT_FOR_VM": FineTuningJobStatus.QUEUED,
    "FOUND_VM": FineTuningJobStatus.QUEUED,
    "DETACHED_VM": FineTuningJobStatus.QUEUED,
}

async def update_job_statuses() -> None:
    """Update the status of all non-terminal jobs."""
    async with AsyncSessionLocal() as db:
        try:
            # Get jobs that need updates
            jobs = await get_jobs_for_update(db)
            if not jobs:
                logger.info("No jobs found for status update")
                return

            # Group jobs by user for scheduler API
            jobs_by_user = group_jobs_by_user(jobs)

            # Update each group of jobs
            for user_id, job_ids in jobs_by_user.items():
                await update_job_group(db, user_id, job_ids)

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update job statuses: {str(e)}")

async def get_jobs_for_update(db: AsyncSession) -> List[Dict[str, Any]]:
    """Get jobs that need status updates."""
    non_terminal_statuses = [
        FineTuningJobStatus.NEW,
        FineTuningJobStatus.QUEUED,
        FineTuningJobStatus.RUNNING,
        FineTuningJobStatus.STOPPING
    ]

    recent_completed_cutoff = datetime.utcnow() - timedelta(minutes=10)

    return await ft_queries.get_jobs_for_status_update(
        db,
        non_terminal_statuses,
        recent_completed_cutoff
    )

def group_jobs_by_user(jobs: List[Dict[str, Any]]) -> Dict[UUID, List[UUID]]:
    """Group jobs by user ID for efficient scheduler API calls."""
    jobs_by_user = {}
    for job in jobs:
        if job.user_id not in jobs_by_user:
            jobs_by_user[job.user_id] = []
        jobs_by_user[job.user_id].append(job.id)
    return jobs_by_user

async def update_job_group(
        db: AsyncSession,
        user_id: UUID,
        job_ids: List[UUID]
) -> None:
    """Update a group of jobs for a single user."""
    try:
        # Get updates from scheduler
        job_updates = await fetch_job_details(user_id, job_ids)

        # Process each job update
        for update in job_updates:
            await process_job_update(db, update, user_id)

        await db.commit()
        logger.info(f"Updated {len(job_updates)} jobs for user {user_id}")

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update jobs for user {user_id}: {str(e)}")

async def process_job_update(
        db: AsyncSession,
        update: Dict[str, Any],
        user_id: UUID
) -> None:
    """Process a single job update from the scheduler."""
    job_id = update['job_id']

    # Get job from database
    job = await ft_queries.get_job_with_details(db, UUID(job_id))
    if not job:
        logger.warning(f"Job not found for update: {job_id}")
        return

    # Update job status
    new_status = STATUS_MAPPING.get(update['status']) or update['status']
    if job.status != new_status:
        job.status = new_status
        logger.info(f"Updated status for job {job_id} to {new_status}")

    # Update timestamps
    await update_job_timestamps(job, update['timestamps'])

    # Update progress
    await update_job_steps(db, job, user_id, update['artifacts'])

    # Create fine-tuned model if needed
    await check_create_model(db, job_id, user_id, update['artifacts'])

async def update_job_timestamps(
        job: Any,
        timestamps: Dict[str, str]
) -> None:
    """Update job timestamps from scheduler data."""
    job_timestamps = job.details.timestamps.copy()

    for event, timestamp in timestamps.items():
        # Map scheduler status to API status if needed
        if event.upper() in STATUS_MAPPING:
            if timestamp:  # Only update if we have a timestamp
                mapped_status = STATUS_MAPPING[event.upper()].lower()
                job_timestamps[mapped_status] = timestamp
        else:
            # Direct update for unmapped statuses
            job_timestamps[event] = timestamp

    job.details.timestamps = job_timestamps

async def update_job_steps(
        db: AsyncSession,
        job: Any,
        user_id: UUID,
        artifacts: Dict[str, Any]
) -> None:
    """Update job progress from artifacts."""
    if not artifacts:
        return

    job_logs = artifacts.get('job_logger', [])
    max_step = 0
    max_epoch = 0
    num_steps = 0
    num_epochs = 0

    for log in job_logs:
        if log.get('operation') == 'step':
            max_step = max(max_step, log['data']['step_num'])
            max_epoch = max(max_epoch, log['data']['epoch_num'])
            num_steps = log['data']['step_len']
            num_epochs = log['data']['epoch_len']

    if job.current_step is None or max_step > job.current_step:
        progress = {
            "current_step": max_step,
            "total_steps": num_steps,
            "current_epoch": max_epoch,
            "total_epochs": num_epochs,
        }
        await update_job_progress(db, job.id, user_id, progress)

async def check_create_model(
        db: AsyncSession,
        job_id: UUID,
        user_id: UUID,
        artifacts: Dict[str, Any]
) -> None:
    """Check and create fine-tuned model if weights are available."""
    if not artifacts:
        return

    for log in artifacts.get('job_logger', []):
        if log.get('operation') == 'weights':
            await create_fine_tuned_model(db, UUID(job_id), user_id, log['data'])
