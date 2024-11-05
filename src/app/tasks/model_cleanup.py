from datetime import datetime, timedelta

from google.api_core.exceptions import NotFound
from google.cloud import storage
from sqlalchemy import select

from app.core.config_manager import config
from app.core.constants import FineTunedModelStatus
from app.core.database import AsyncSessionLocal
from app.core.utils import setup_logger
from app.models.fine_tuned_model import FineTunedModel

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def cleanup_deleted_model_weights():
    """
    Clean up weights files from GCS for models that have been marked as deleted
    """
    async with AsyncSessionLocal() as db:
        # Find jobs marked as deleted more than 7 days ago
        search_interval = datetime.utcnow() - timedelta(days=3)
        result = await db.execute(
            select(FineTunedModel)
            .where(
                FineTunedModel.status == FineTunedModelStatus.DELETED,
                FineTunedModel.updated_at >= search_interval
            )
        )
        deleted_models = result.scalars().all()

        if not deleted_models:
            logger.info("No deleted jobs found for cleanup")
            return

        for model in deleted_models:
            if model.artifacts:
                try:
                    # Extract bucket name and user_id, job_id from base_url
                    base_url = model.artifacts['base_url']
                    bucket_name = base_url.split('/')[3]
                    user_id, job_id = base_url.split('/')[4:6]
                    # Initialize GCS client
                    storage_client = storage.Client()
                    bucket = storage_client.bucket(bucket_name)
                    # Delete weights files from GCS
                    for weight_file in model.artifacts.get('weight_files', []):
                        weight_path = f"{user_id}/{job_id}/{weight_file}"
                        blob = bucket.blob(weight_path)
                        blob.delete()
                        gs_path = f"gs://{bucket_name}/{weight_path}"
                        logger.info(f"Deleted weight file: {gs_path} for model: {model.id}")
                    # Update artifacts to remove weights files
                    model.artifacts['weights_files'] = []
                    await db.commit()
                except NotFound:
                    # Weight wasn't found in GCS, continue
                    pass
                except Exception as e:
                    logger.error(f"Error deleting weights for model {model.id}: {str(e)}")
                    pass