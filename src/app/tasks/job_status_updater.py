from typing import Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config_manager import config
from app.core.constants import FineTuningJobStatus
from app.core.database import AsyncSessionLocal
from app.core.scheduler_client import fetch_job_details
from app.core.utils import setup_logger
from app.models.fine_tuning_job import FineTuningJob
from app.services.fine_tuned_model import create_fine_tuned_model

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
        result = await db.execute(
            select(FineTuningJob)
            .options(selectinload(FineTuningJob.details))
            .where(FineTuningJob.status.in_(non_terminal_statuses))
        )
        jobs = result.scalars().all()

        if not jobs:
            logger.info("No non-terminal jobs found for status update")
            return

        # Group jobs by user_id; because that's how the Scheduler API expects them
        jobs_by_user = {}
        # Also group by job_id for easier status update
        job_ids_to_jobs: Dict[str, FineTuningJob] = {}
        for job in jobs:
            # Store the job in a dictionary for easier access later
            job_ids_to_jobs[str(job.id)] = job
            # Group jobs by user_id
            if job.user_id not in jobs_by_user:
                jobs_by_user[job.user_id] = []
            jobs_by_user[job.user_id].append(job.id)

        # Update jobs for each user
        for user_id, job_ids in jobs_by_user.items():
            # Poll the Scheduler API for job updates, grouped by user
            job_updates = await fetch_job_details(user_id, job_ids)

            # Update job in the API database
            # 1. Update the status
            # 2. Update the timestamps
            for job_update in job_updates:
                job_id = job_update['job_id']
                # Find the job in the list of jobs that we already fetched from the database
                job = job_ids_to_jobs.get(job_id)

                # 1. Update the status

                # Map the status from the Scheduler API to our internal status
                # We hide some statuses from the Scheduler API and map them to API statuses
                new_status = STATUS_MAPPING.get(job_update['status']) or job_update['status']
                # Update the status if it's different
                if job and job.status != new_status:
                    job.status = new_status
                    logger.info(f"Updated status for job {job_id} to {new_status}")

                # 2. Update the timestamps

                # Update timestamps in details table
                timestamps = job.details.timestamps.copy()
                for event, timestamp in job_update['timestamps'].items():
                    # Map the status from the Scheduler API to the API status
                    if event.upper() in STATUS_MAPPING:
                        # If there's no timestamp, don't update it,
                        # because multiple Scheduler statuses can map to the same API status
                        # we don't want to overwrite an existing API timestamp
                        # with an empty Scheduler timestamp
                        if timestamp:
                            timestamps[STATUS_MAPPING[event.upper()].lower()] = timestamp
                    else:
                        # If the event is not in the mapping, just update it
                        timestamps[event] = timestamp
                # Update the timestamps in the database;
                # note that we're updating the entire dictionary
                # otherwise, the changes won't be detected by SQLAlchemy
                job.details.timestamps = timestamps

                # 3. Create fine-tuned model if artifacts are available

                #  Look through all artifacts for weights
                artifacts = job_update['artifacts']
                if artifacts:
                    # Weights are under the job_logger section in the artifacts
                    for x in artifacts.get('job_logger', []):
                        if x.get('operation') == 'weights':
                            await create_fine_tuned_model(db, UUID(job_id), UUID(user_id), x['data'])


            # Commit the changes for the user
            await db.commit()
            logger.info(f"Successfully updated statuses for {len(job_updates)} jobs for user {user_id}")
