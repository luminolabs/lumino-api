from uuid import UUID
import aiohttp

from app.constants import FineTuningJobStatus
from app.database import AsyncSessionLocal
from app.models.fine_tuning_job import FineTuningJob
from app.models.fine_tuning_job_detail import FineTuningJobDetail
from app.models.dataset import Dataset
from app.models.base_model import BaseModel
from sqlalchemy import select
from app.config_manager import config

INTERNAL_API_URL = config.scheduler_zen_url


async def start_fine_tuning_job(job_id: UUID):
    """
    Start a fine-tuning job asynchronously using the internal API.

    :param job_id: The ID of the fine-tuning job to start
    """
    async with AsyncSessionLocal() as db:
        # Fetch job details
        result = await db.execute(
            select(FineTuningJob, Dataset, BaseModel, FineTuningJobDetail)
            .join(Dataset, FineTuningJob.dataset_id == Dataset.id)
            .join(BaseModel, FineTuningJob.base_model_id == BaseModel.id)
            .join(FineTuningJobDetail, FineTuningJob.id == FineTuningJobDetail.fine_tuning_job_id)
            .where(FineTuningJob.id == job_id)
        )
        job, dataset, base_model, job_detail = result.first()

    try:
        # Prepare the payload for the internal API
        payload = {
            "job_id": str(job_id),
            "workflow": "torchtunewrapper",
            "args": {
                "job_config_name": base_model.name,
                "dataset_id": dataset.id,
                "train_file_path": dataset.storage_url.split("/")[-1],
                "batch_size": job_detail.parameters.get("batch_size", 2),
                "shuffle": job_detail.parameters.get("shuffle", True),
                "num_epochs": job_detail.parameters.get("num_epochs", 1),
                "use_lora": job_detail.parameters.get("use_lora", True),
                "use_single_device": job_detail.parameters.get("use_single_device", False),
                "num_gpus": job_detail.parameters.get("num_gpus", 4)
            },
            "keep_alive": False,
            "cluster": job_detail.parameters.get("cluster", "4xa100-40gb")
        }

        # Send request to internal API
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{INTERNAL_API_URL}/jobs", json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    # Update job with response data if needed
                    async with AsyncSessionLocal() as db:
                        job = await db.get(FineTuningJob, job_id)
                        job.status = FineTuningJobStatus.NEW
                        job.details.internal_job_id = response_data.get("internal_job_id")
                        await db.commit()
                else:
                    raise Exception(f"Failed to start fine-tuning job: {await response.text()}")

    except Exception as e:
        print(f"Error starting fine-tuning job: {e}")
        async with AsyncSessionLocal() as db:
            job = await db.get(FineTuningJob, job_id)
            job.status = FineTuningJobStatus.FAILED
            job.details.error_message = e.detail
            await db.commit()


async def cancel_fine_tuning_job_task(job_id: UUID):
    """
    Cancel a fine-tuning job using the internal API.

    :param job_id: The ID of the fine-tuning job to cancel
    """
    async with AsyncSessionLocal() as db:
        job = await db.get(FineTuningJob, job_id)
        if not job:
            raise ValueError("Fine-tuning job not found")

        internal_job_id = job.details.internal_job_id

    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{INTERNAL_API_URL}/jobs/{internal_job_id}") as response:
                if response.status == 200:
                    async with AsyncSessionLocal() as db:
                        job = await db.get(FineTuningJob, job_id)
                        job.status = FineTuningJobStatus.STOPPING
                        await db.commit()
                else:
                    raise Exception(f"Failed to cancel fine-tuning job: {await response.text()}")

    except Exception as e:
        print(f"Error cancelling fine-tuning job: {e}")
        raise


async def get_job_logs(job_id: UUID) -> str:
    """
    Get logs for a fine-tuning job from the internal API.

    :param job_id: The ID of the fine-tuning job
    :return: The logs as a string
    """
    async with AsyncSessionLocal() as db:
        job = await db.get(FineTuningJob, job_id)
        if not job:
            raise ValueError("Fine-tuning job not found")

        internal_job_id = job.details.internal_job_id

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{INTERNAL_API_URL}/jobs/{internal_job_id}/logs") as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"Failed to get job logs: {await response.text()}")

    except Exception as e:
        print(f"Error getting job logs: {e}")
        raise


async def check_job_status(job_id: UUID):
    """
    Check the status of a fine-tuning job using the internal API.

    :param job_id: The ID of the fine-tuning job
    """
    async with AsyncSessionLocal() as db:
        job = await db.get(FineTuningJob, job_id)
        if not job:
            raise ValueError("Fine-tuning job not found")

        internal_job_id = job.details.internal_job_id

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{INTERNAL_API_URL}/jobs/{internal_job_id}") as response:
                if response.status == 200:
                    job_data = await response.json()
                    async with AsyncSessionLocal() as db:
                        job = await db.get(FineTuningJob, job_id)
                        job.status = job_data.get("status", job.status)
                        job.current_step = job_data.get("current_step")
                        job.total_steps = job_data.get("total_steps")
                        job.details.metrics = job_data.get("metrics", {})
                        await db.commit()
                else:
                    raise Exception(f"Failed to check job status: {await response.text()}")

    except Exception as e:
        print(f"Error checking job status: {e}")
        raise
