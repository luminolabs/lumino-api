from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.common import paginate_query
from app.core.config_manager import config
from app.core.exceptions import (
    BaseModelNotFoundError
)
from app.core.utils import setup_logger
from app.models.base_model import BaseModel
from app.schemas.common import Pagination
from app.schemas.model import BaseModelResponse

# Set up logger
logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)


async def get_base_models(
        db: AsyncSession,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[BaseModelResponse], Pagination]:
    """
    Get all available base LLM models with pagination.

    Args:
        db (AsyncSession): The database session.
        page (int): The page number for pagination.
        items_per_page (int): The number of items per page.

    Returns:
        tuple[list[BaseModelResponse], Pagination]: A tuple containing the list of base models and pagination info.
    """
    # Construct the query, select all except name='llm_dummy'
    query = (select(BaseModel).where(BaseModel.name != 'llm_dummy').order_by(BaseModel.name.desc()))
    # Paginate the query
    models, pagination = await paginate_query(db, query, page, items_per_page)
    # Create response objects
    model_responses = [BaseModelResponse.from_orm(model) for model in models]
    # Log and return objects
    logger.info(f"Retrieved {len(model_responses)} base models, page: {page}")
    return model_responses, pagination


async def get_base_model(db: AsyncSession, model_name: str) -> BaseModelResponse:
    """
    Get a specific base model.

    Args:
        db (AsyncSession): The database session.
        model_name (str): The name of the base model.

    Returns:
        BaseModelResponse: The base model if found.

    Raises:
        BaseModelNotFoundError: If the specified base model is not found.
    """
    # Get the base model from the database
    model = (await db.execute(
        select(BaseModel)
        .where(BaseModel.name == model_name)
    )).scalar_one_or_none()

    # Raise an error if the base model is not found
    if not model:
        raise BaseModelNotFoundError(f"Base model not found: {model_name}", logger)

    # Log and return the base model
    logger.info(f"Retrieved base model: {model_name}")
    return BaseModelResponse.from_orm(model)
