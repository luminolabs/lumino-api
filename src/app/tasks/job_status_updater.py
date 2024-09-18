from sqlalchemy import select

from app.core.config_manager import config
from app.core.constants import FineTuningJobStatus
from app.core.database import AsyncSessionLocal
from app.core.scheduler_client import fetch_job_details
from app.core.utils import setup_logger
from app.models.fine_tuning_job import FineTuningJob

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)

# Map the job status from the Scheduler API to our internal status
STATUS_MAPPING = {
    "WAIT_FOR_VM": FineTuningJobStatus.QUEUED,
    "FOUND_VM": FineTuningJobStatus.QUEUED,
    "DETACHED_VM": FineTuningJobStatus.QUEUED,
}

async def update_job_statuses():
    """
    Update the status of all non-terminal fine-tuning jobs.
    """
    async with AsyncSessionLocal() as db:
        # We're interested in all non-terminal jobs statuses
        # because all other statuses are terminal and won't be updated ever again
        # Excluded statuses: SUCCEEDED, FAILED, STOPPED
        non_terminal_statuses = [
            FineTuningJobStatus.NEW,
            FineTuningJobStatus.QUEUED,
            FineTuningJobStatus.RUNNING,
            FineTuningJobStatus.STOPPING
        ]
        query = select(FineTuningJob).where(FineTuningJob.status.in_(non_terminal_statuses))
        result = await db.execute(query)
        jobs = result.scalars().all()

        if not jobs:
            logger.info("No non-terminal jobs found for status update")
            return

        # Group jobs by user_id; because that's how the Scheduler API expects them
        jobs_by_user = {}
        # Also group by job_id for easier status update
        job_ids_to_jobs = {}
        for job in jobs:
            # Store the job in a dictionary for easier access later
            job_ids_to_jobs[str(job.id)] = job
            # Group jobs by user_id
            if job.user_id not in jobs_by_user:
                jobs_by_user[job.user_id] = []
            jobs_by_user[job.user_id].append(job.id)

        # Update job statuses for each user
        for user_id, job_ids in jobs_by_user.items():
            # Poll the Scheduler API for job statuses
            updated_statuses = await fetch_job_details(user_id, job_ids)
            # Update the statuses in the database
            for status in updated_statuses:
                job_id = status['job_id']
                # Map the status from the Scheduler API to our internal status
                new_status = STATUS_MAPPING.get(status['status']) or status['status']
                # Find the job in the list of jobs that we already fetched from the database
                job = job_ids_to_jobs.get(job_id)
                if job and job.status != new_status:
                    job.status = new_status
                    logger.info(f"Updated status for job {job_id} to {new_status}")

            await db.commit()
            logger.info(f"Successfully updated statuses for {len(updated_statuses)} jobs for user {user_id}")
