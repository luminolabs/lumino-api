from uuid import UUID
import aiohttp

from app.constants import FineTuningJobStatus
from app.database import AsyncSessionLocal
from app.models.base_model import BaseModel
from app.models.fine_tuned_model import FineTunedModel
from sqlalchemy import select
from app.config_manager import config
from app.models.fine_tuning_job import FineTuningJob

INTERNAL_API_URL = config.internal_api_url


async def list_base_models():
    """
    Fetch the list of available base models from the internal API.

    :return: List of base models
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{INTERNAL_API_URL}/models/base") as response:
                if response.status == 200:
                    models_data = await response.json()
                    async with AsyncSessionLocal() as db:
                        for model_data in models_data:
                            existing_model = await db.execute(
                                select(BaseModel).where(BaseModel.id == model_data['id'])
                            )
                            if existing_model.scalar_one_or_none() is None:
                                new_model = BaseModel(**model_data)
                                db.add(new_model)
                        await db.commit()
                    return models_data
                else:
                    raise Exception(f"Failed to fetch base models: {await response.text()}")
    except Exception as e:
        print(f"Error fetching base models: {e}")
        raise


async def get_base_model_details(model_id: UUID):
    """
    Fetch details of a specific base model from the internal API.

    :param model_id: The ID of the base model
    :return: Base model details
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{INTERNAL_API_URL}/models/base/{model_id}") as response:
                if response.status == 200:
                    model_data = await response.json()
                    async with AsyncSessionLocal() as db:
                        existing_model = await db.get(BaseModel, model_id)
                        if existing_model:
                            for key, value in model_data.items():
                                setattr(existing_model, key, value)
                        else:
                            new_model = BaseModel(**model_data)
                            db.add(new_model)
                        await db.commit()
                    return model_data
                else:
                    raise Exception(f"Failed to fetch base model details: {await response.text()}")
    except Exception as e:
        print(f"Error fetching base model details: {e}")
        raise


async def create_fine_tuned_model(fine_tuning_job_id: UUID):
    """
    Create a fine-tuned model entry after a successful fine-tuning job.

    :param fine_tuning_job_id: The ID of the completed fine-tuning job
    :return: Fine-tuned model details
    """
    async with AsyncSessionLocal() as db:
        job = await db.get(FineTuningJob, fine_tuning_job_id)
        if not job or job.status != FineTuningJobStatus.SUCCEEDED:
            raise ValueError("Fine-tuning job not found or not completed")

        new_model = FineTunedModel(
            user_id=job.user_id,
            fine_tuning_job_id=job.id,
            name=f"ft-{job.base_model.name}-{job.id}",
            description=f"Fine-tuned model based on {job.base_model.name}",
            artifacts={}  # This should be populated with actual artifacts data
        )
        db.add(new_model)
        await db.commit()
        await db.refresh(new_model)
        return new_model


async def get_fine_tuned_model_details(model_id: UUID):
    """
    Fetch details of a specific fine-tuned model.

    :param model_id: The ID of the fine-tuned model
    :return: Fine-tuned model details
    """
    async with AsyncSessionLocal() as db:
        model = await db.get(FineTunedModel, model_id)
        if not model:
            raise ValueError("Fine-tuned model not found")
        return model


async def delete_fine_tuned_model(model_id: UUID):
    """
    Delete a fine-tuned model.

    :param model_id: The ID of the fine-tuned model to delete
    """
    async with AsyncSessionLocal() as db:
        model = await db.get(FineTunedModel, model_id)
        if not model:
            raise ValueError("Fine-tuned model not found")

        # Here you might want to add logic to delete the model from your ML infrastructure
        # For now, we'll just mark it as deleted in the database
        await db.delete(model)
        await db.commit()


async def sync_models_with_internal_api():
    """
    Synchronize the local database with the models available in the internal API.
    This function should be run periodically to keep the local database up-to-date.
    """
    try:
        # Sync base models
        await list_base_models()

        # Sync fine-tuned models (assuming the internal API provides this endpoint)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{INTERNAL_API_URL}/models/fine-tuned") as response:
                if response.status == 200:
                    fine_tuned_models = await response.json()
                    async with AsyncSessionLocal() as db:
                        for model_data in fine_tuned_models:
                            existing_model = await db.execute(
                                select(FineTunedModel).where(FineTunedModel.id == model_data['id'])
                            )
                            if existing_model.scalar_one_or_none() is None:
                                new_model = FineTunedModel(**model_data)
                                db.add(new_model)
                            else:
                                for key, value in model_data.items():
                                    setattr(existing_model.scalar_one(), key, value)
                        await db.commit()
                else:
                    raise Exception(f"Failed to fetch fine-tuned models: {await response.text()}")
    except Exception as e:
        print(f"Error synchronizing models: {e}")
        raise
