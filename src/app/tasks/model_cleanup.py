from datetime import timedelta
from typing import Any, Optional

from google.api_core.exceptions import NotFound
from google.cloud import storage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.utils import setup_logger
from app.queries import models as model_queries
from app.queries.common import now_utc

logger = setup_logger(__name__)


async def cleanup_deleted_model_weights(db: Optional[AsyncSession] = None) -> None:
    """Wrapper to _update_job_statuses that handles database session."""
    if db is None:
        async with AsyncSessionLocal() as db:
            await _cleanup_deleted_model_weights(db)
    else:
        await _cleanup_deleted_model_weights(db)


async def _cleanup_deleted_model_weights(db: AsyncSession) -> None:
    """Clean up weights files from GCS for deleted models."""
    try:
        # Find recently deleted models
        cutoff_date = now_utc() - timedelta(days=3)
        deleted_models = await model_queries.get_deleted_models(
            db,
            cutoff_date
        )

        if not deleted_models:
            logger.info("No deleted models found for cleanup")
            return

        storage_client = storage.Client()

        for model in deleted_models:
            await _cleanup_model_weights(model, storage_client)

        await db.commit()

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to cleanup model weights: {str(e)}")


async def _cleanup_model_weights(
        model: Any,
        storage_client: storage.Client
) -> None:
    """Clean up weights for a single model."""
    if not model.artifacts:
        return

    try:
        # Extract bucket and path information
        base_url = model.artifacts['base_url']
        bucket_name = base_url.split('/')[3]
        user_id, job_id = base_url.split('/')[4:6]
        bucket = storage_client.bucket(bucket_name)

        # Delete each weight file
        for weight_file in model.artifacts.get('weight_files', []):
            weight_path = f"{user_id}/{job_id}/{weight_file}"
            blob = bucket.blob(weight_path)
            try:
                blob.delete()
                gs_path = f"gs://{bucket_name}/{weight_path}"
                logger.info(f"Deleted weight file: {gs_path}")
            except NotFound:
                # Weight file already deleted, continue
                pass

        # Update artifacts to remove weight files
        model.artifacts['weight_files'] = []

    except Exception as e:
        logger.error(
            f"Error deleting weights for model {model.id}: {str(e)}"
        )
