from datetime import timedelta
from typing import Optional, Dict, Any

from gcloud.aio.storage import Storage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.utils import setup_logger
from app.models.fine_tuned_model import FineTunedModel
from app.queries import models as model_queries
from app.queries.common import now_utc

logger = setup_logger(__name__)


async def cleanup_deleted_model_weights(db: Optional[AsyncSession] = None) -> None:
    """Wrapper to _cleanup_deleted_model_weights that handles database session."""
    if db is None:
        async with AsyncSessionLocal() as db:
            await _cleanup_deleted_model_weights(db)
    else:
        await _cleanup_deleted_model_weights(db)


async def _cleanup_deleted_model_weights(db: AsyncSession) -> None:
    """Clean up weights files from GCS for deleted models."""
    try:
        logger.info("Starting model weights cleanup")

        # Find recently deleted models (within last 3 days)
        cutoff_date = now_utc() - timedelta(days=3)
        deleted_models = await model_queries.get_deleted_models(
            db,
            cutoff_date
        )
        logger.info(f"Found {len(deleted_models)} deleted models for cleanup")

        if not deleted_models:
            return

        storage = Storage()
        for model in deleted_models:
            await _cleanup_model_weights(model, storage)

        await db.commit()
        logger.info("Model weights cleanup complete")

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to cleanup model weights: {str(e)}")


async def _cleanup_model_weights(model: FineTunedModel, storage: Storage) -> None:
    """Clean up weights for a single model."""
    if not model.artifacts:
        logger.info(f"Model {model.id} has no artifacts, skipping")
        return

    logger.info(f"Cleaning up weights for model {model.id}")

    # Extract bucket and path information
    base_url = model.artifacts['base_url']
    # Parse gs://bucket-name/path/to/file format
    bucket_name = base_url.split('/')[3]
    user_id, job_id = base_url.split('/')[4:6]

    # Delete each weight file
    for weight_file in model.artifacts.get('weight_files', []):
        weight_path = f"{user_id}/{job_id}/{weight_file}"
        try:
            await storage.delete(bucket=bucket_name, object_name=weight_path)
            gs_path = f"gs://{bucket_name}/{weight_path}"
            logger.info(f"Deleted weight file: {gs_path}")
        except Exception as e:
            # Log error and continue with next file, we don't want to stop the cleanup process
            if "404" in str(e):
                logger.warning(f"Weight file not found: {weight_path}, model {model.id}")
            else:
                logger.error(f"Error deleting weight file {weight_path}, model {model.id}: {str(e)}")

    # Update artifacts to remove weight files
    artifacts = _update_model_artifacts(model.artifacts)
    model.artifacts = artifacts

    logger.info(f"Deleted weights for model {model.id}")


def _update_model_artifacts(artifacts: Dict[str, Any]) -> Dict[str, Any]:
    """Update model artifacts to remove weight files."""
    updated_artifacts = artifacts.copy()
    updated_artifacts['weight_files'] = []
    return updated_artifacts
