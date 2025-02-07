from typing import List, Dict, Any
from uuid import UUID

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.constants import FineTuningJobStatus
from app.core.exceptions import (
    FineTuningJobCreationError,
    FineTuningJobRefreshError,
    FineTuningJobCancellationError
)
from app.core.utils import setup_logger
from app.queries import fine_tuning as ft_queries
from app.services.dataset import get_dataset_bucket

logger = setup_logger(__name__)

INTERNAL_API_URL = config.scheduler_zen_url


async def start_fine_tuning_job(db: AsyncSession, job_id: UUID, user_id: UUID) -> None:
    """Start a fine-tuning job via scheduler."""
    if not config.run_with_scheduler:
        logger.info("Scheduler API is disabled")
        return

    # Get job with all required information
    job_info = await ft_queries.get_job_with_details_full(db, job_id, user_id)
    if not job_info:
        raise FineTuningJobCreationError(
            f"Failed to find job: {job_id}",
            logger
        )

    job, dataset, base_model, job_detail = job_info

    # Extract cluster configuration
    use_lora = job_detail.parameters.get("use_lora", True)
    use_qlora = job_detail.parameters.get("use_qlora", False)

    # Prevent full fine-tuning
    if not use_lora and not use_qlora:
        raise FineTuningJobCreationError(
            "Full fine-tuning is currently disabled",
            logger
        )

    if not use_lora:
        use_qlora = False

    cluster_config_name = (
        f"{'q' if use_qlora else ''}"
        f"{'lora' if use_lora else 'full'}"
    )

    cluster_config = base_model.cluster_config.get(cluster_config_name)
    num_gpus = cluster_config.get("num_gpus")
    gpu_type = cluster_config.get("gpu_type")

    # Prepare scheduler payload
    payload = {
        "job_id": str(job_id),
        "workflow": "torchtunewrapper",
        "args": {
            "job_config_name": base_model.name,
            "dataset_id": (
                f"gs://{get_dataset_bucket()}/{user_id}/"
                f"{dataset.file_name}"
            ),
            "batch_size": job_detail.parameters.get("batch_size", 2),
            "shuffle": job_detail.parameters.get("shuffle", True),
            "num_epochs": job_detail.parameters.get("num_epochs", 1),
            "use_lora": use_lora,
            "use_qlora": use_qlora,
            "num_gpus": num_gpus,
        },
        "gpu_type": gpu_type,
        "num_gpus": num_gpus,
        "user_id": str(job.user_id),
        "keep_alive": False,
    }

    if config.env_name in ("dev", "prod"):
        payload["args"]["override_env"] = config.env_name

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f"{INTERNAL_API_URL}/jobs/{job.provider.value.lower()}",
                    json=payload
            ) as response:
                if response.status == 200:
                    logger.info(f"Started fine-tuning job: {job_id}")
                elif response.status == 422:
                    error_data = await response.json()
                    raise FineTuningJobCreationError(
                        f"Failed to start job {job_id}: {error_data['message']}",
                        logger
                    )
                else:
                    raise FineTuningJobCreationError(
                        f"Failed to start job {job_id}: {await response.text()}",
                        logger
                    )

    except Exception as e:
        # Update job status to failed
        job.status = FineTuningJobStatus.FAILED
        await db.commit()
        raise FineTuningJobCreationError(
            f"Failed to start job {job_id}: {str(e)}",
            logger
        )


async def fetch_job_details(
        user_id: UUID,
        job_ids: List[UUID]
) -> List[Dict[str, Any]]:
    """
    Get job status updates from scheduler.

    Args:
        user_id: User ID
        job_ids: List of job IDs to check

    Returns:
        List of job status details

    Raises:
        FineTuningJobRefreshError: If update fails
    """
    if not config.run_with_scheduler:
        logger.info("Scheduler API is disabled")
        return []

    user_id_str = str(user_id)
    job_ids_str = [str(job_id) for job_id in job_ids]

    async with aiohttp.ClientSession() as session:
        async with session.post(
                f"{INTERNAL_API_URL}/jobs/get_by_user_and_ids",
                json={"user_id": user_id_str, "job_ids": job_ids_str}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise FineTuningJobRefreshError(
                    f"Error refreshing job statuses: {await response.text()}"
                )


async def stop_fine_tuning_job(job_id: UUID, user_id: UUID) -> None:
    """
    Stop a running fine-tuning job.

    Args:
        job_id: Job ID to stop
        user_id: User ID

    Raises:
        FineTuningJobCancellationError: If stop request fails
    """
    if not config.run_with_scheduler:
        logger.info("Scheduler API is disabled")
        return

    async with aiohttp.ClientSession() as session:
        async with session.post(
                f"{INTERNAL_API_URL}/jobs/gcp/stop/{job_id}/{user_id}"
        ) as response:
            if response.status == 200:
                logger.info(f"Requested stop for job: {job_id}")
                return await response.json()
            elif response.status == 404:
                raise FineTuningJobCancellationError(
                    f"Job not found or not running: {job_id}",
                    logger
                )
            else:
                raise FineTuningJobCancellationError(
                    f"Failed to stop job {job_id}: {await response.text()}",
                    logger
                )
