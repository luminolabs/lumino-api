from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_manager import config
from app.core.exceptions import BaseModelNotFoundError
from app.core.utils import setup_logger
from app.queries import models as model_queries
from app.schemas.common import Pagination
from app.schemas.model import BaseModelResponse

logger = setup_logger(__name__, add_stdout=config.log_stdout, log_level=config.log_level)

async def get_base_models(
        db: AsyncSession,
        page: int = 1,
        items_per_page: int = 20
) -> tuple[list[BaseModelResponse], Pagination]:
    """Get all available base LLM models with pagination."""
    offset = (page - 1) * items_per_page

    # Get total count and paginated results
    total_count = await model_queries.count_base_models(db)
    models = await model_queries.list_base_models(db, offset, items_per_page)

    # Calculate pagination
    total_pages = (total_count + items_per_page - 1) // items_per_page
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
    )

    # Create response objects
    model_responses = [BaseModelResponse.from_orm(model) for model in models]

    logger.info(f"Retrieved {len(model_responses)} base models, page: {page}")
    return model_responses, pagination

async def get_base_model(db: AsyncSession, model_name: str) -> BaseModelResponse:
    """Get detailed information about a specific base model."""
    model = await model_queries.get_base_model_by_name(db, model_name)
    if not model:
        raise BaseModelNotFoundError(f"Base model not found: {model_name}", logger)

    logger.info(f"Retrieved base model: {model_name}")
    return BaseModelResponse.from_orm(model)
