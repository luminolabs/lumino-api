import aiohttp

from app.database import AsyncSessionLocal
from app.models.base_model import BaseModel
from sqlalchemy import select
from app.config_manager import config
from app.core.exceptions import (
    ModelRetrievalError,
)
from app.utils import setup_logger

INTERNAL_API_URL = config.internal_api_url

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def list_base_models() -> list[dict]:
    """
    Fetch the list of available base models from the internal API.

    Returns:
        list[dict]: List of base models.

    Raises:
        ModelRetrievalError: If there's an error fetching the base models.
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
                    logger.info(f"Successfully retrieved {len(models_data)} base models")
                    return models_data
                else:
                    raise ModelRetrievalError(f"Failed to fetch base models: {await response.text()}")
    except Exception as e:
        logger.error(f"Error fetching base models: {str(e)}")
        raise ModelRetrievalError(f"Failed to fetch base models: {str(e)}")
