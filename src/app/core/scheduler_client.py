from typing import List, Dict, Any
from uuid import UUID
import aiohttp

from app.core.constants import FineTuningJobStatus
from app.core.database import AsyncSessionLocal
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.models.dataset import Dataset
from app.models.base_model import BaseModel
from sqlalchemy import select
from app.core.config_manager import config
from app.core.utils import setup_logger
from app.core.exceptions import FineTuningJobCreationError, FineTuningJobRefreshError, FineTuningJobCancellationError
from app.models.user import User

INTERNAL_API_URL = config.scheduler_zen_url

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def start_fine_tuning_job(job_id: UUID):
    """
    Start a fine-tuning job asynchronously using the Scheduler API.

    Args:
        job_id (UUID): The ID of the fine-tuning job to start.

    Raises:
        FineTuningJobCreationError: If there's an error starting the fine-tuning job.
    """
    if not config.run_with_scheduler:
        logger.info("Scheduler API is disabled; `run_with_scheduler` is set to False.")
        return

    async with AsyncSessionLocal() as db:
        # Fetch job details
        result = await db.execute(
            select(FineTuningJob, Dataset, BaseModel, FineTuningJobDetail, User)
            .join(Dataset, FineTuningJob.dataset_id == Dataset.id)
            .join(BaseModel, FineTuningJob.base_model_id == BaseModel.id)
            .join(FineTuningJobDetail, FineTuningJob.id == FineTuningJobDetail.fine_tuning_job_id)
            .join(User, FineTuningJob.user_id == User.id)
            .where(FineTuningJob.id == job_id)
        )
        job, dataset, base_model, job_detail, user = result.first()

    # Extract cluster configuration for requested model and fine-tuning type (LoRA or full)
    # While we can use arbitrary cluster configurations internally,
    # we would want to enforce certain cluster configurations on the Customer API, based
    # on our pricing plans and strategy
    use_lora = job_detail.parameters.get("use_lora", True)
    use_qlora = job_detail.parameters.get("use_qlora", False)
    if not use_lora:
        use_qlora = False
    # "qlora" or "lora" or "full"
    cluster_config_name = f"{'q' if use_qlora else ''}{'lora' if use_lora else 'full'}"

    cluster_config = base_model.cluster_config.get(cluster_config_name)
    num_gpus = cluster_config.get("num_gpus")  # ex: 4
    gpu_type = cluster_config.get("gpu_type")  # ex: "a100-40gb"

    # Prepare the payload for the Scheduler API
    payload = {
        "job_id": str(job_id),
        "workflow": "torchtunewrapper",
        "args": {
            "job_config_name": base_model.name,
            "dataset_id": f"gs://{config.gcs_bucket}/datasets/{user.id}/" + dataset.file_name,
            "batch_size": job_detail.parameters.get("batch_size", 2),
            "shuffle": job_detail.parameters.get("shuffle", True),
            "num_epochs": job_detail.parameters.get("num_epochs", 1),
            "use_lora": use_lora,
            "use_qlora": use_qlora,
            "num_gpus": num_gpus,
        },
        "gpu_type": gpu_type,
        "user_id": str(job.user_id),
        "keep_alive": False,
    }
    # Add environment name to payload if it's not "local"
    # This allows the pipeline to override the dev environment settings
    # This will not be necessary once we have a separate dev and prod environments
    if config.env_name in ("dev", "prod"):
        payload["args"]["override_env"] = config.env_name

    try:
        # Send request to Scheduler API
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{INTERNAL_API_URL}/jobs", json=payload) as response:
                # Handle successful job creation;
                # no need to update job status because it's already set to `NEW`
                if response.status == 200:
                    logger.info(f"Successfully started fine-tuning job: {job_id}")
                # Handle error responses
                elif response.status == 422:
                    error_data = await response.json()
                    raise FineTuningJobCreationError(
                        f"Failed to start fine-tuning job: {job_id}: {error_data['message']}", logger)
                else:
                    raise FineTuningJobCreationError(
                        f"Failed to start fine-tuning job: {job_id}: {await response.text()}", logger)

    # Handle exceptions and update job status to FAILED
    except Exception as e:
        async with AsyncSessionLocal() as db:
            job = await db.get(FineTuningJob, job_id)
            job.status = FineTuningJobStatus.FAILED
            await db.commit()
        raise FineTuningJobCreationError(f"Failed to start fine-tuning job: {job_id}: {str(e)}", logger)


async def fetch_job_details(user_id: UUID, job_ids: List[UUID]) -> List[Dict[str, Any]]:
    """
    Poll the Scheduler API for the status of multiple jobs.

    Args:
        user_id (UUID): The ID of the user.
        job_ids (List[str]): A list of job IDs to poll.

    Returns:
        List[Dict[str, Any]]: A list of job details.
    """
    if not config.run_with_scheduler:
        logger.info("Scheduler API is disabled; `run_with_scheduler` is set to False.")
        return []

    # Convert UUIDs to strings
    user_id = str(user_id)
    job_ids = [str(job_id) for job_id in job_ids]
    # Send request to Scheduler API
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{INTERNAL_API_URL}/jobs/get_by_user_and_ids", json={"user_id": user_id, "job_ids": job_ids}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise FineTuningJobRefreshError(f"Error refreshing job statuses: {await response.text()}")


async def stop_fine_tuning_job(job_id: UUID):
    """
    Stop a fine-tuning job asynchronously using the Scheduler API.

    Args:
        job_id (UUID): The ID of the fine-tuning job to stop.

    Raises:
        FineTuningJobCancellationError: If there's an error stopping the fine-tuning job.
    """
    if not config.run_with_scheduler:
        logger.info("Scheduler API is disabled; `run_with_scheduler` is set to False.")
        return

    # Send request to Scheduler API
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{INTERNAL_API_URL}/jobs/{job_id}/stop") as response:
            if response.status == 200:
                logger.info(f"Successfully requested to stop fine-tuning job: {job_id}")
                return await response.json()
            elif response.status == 404:
                raise FineTuningJobCancellationError(f"Job not found or not running: {job_id}", logger)
            else:
                raise FineTuningJobCancellationError(f"Failed to stop fine-tuning job: {job_id}: {await response.text()}", logger)