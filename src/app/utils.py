import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import TypeVar, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.config_manager import config
from app.schemas.common import Pagination

T = TypeVar('T')


async def paginate_query(
        db: AsyncSession,
        query: Select,
        page: int,
        items_per_page: int
) -> Tuple[List[T], Pagination]:
    """
    Paginate a query and return the items and pagination object.

    Args:
        db (AsyncSession): The database session.
        query (Select): The SQLAlchemy query.
        page (int): The page number.
        items_per_page (int): The number of items per page.
    Returns:
        Tuple[List[T], Pagination]: A tuple of the items and pagination object.
    """
    # Count total items
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)

    # Calculate pagination
    total_pages = (total_count + items_per_page - 1) // items_per_page
    offset = (page - 1) * items_per_page

    # Fetch items
    result = await db.execute(query.offset(offset).limit(items_per_page))
    items = result.scalars().all()

    # Create pagination object
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
    )

    # Return items and pagination
    return items, pagination


def setup_logger(name: str,
                 add_stdout: bool = True,
                 log_level: int = logging.INFO) -> logging.Logger:
    """
    Sets up a logger

    Args:
        name (str): The name of the logger.
        add_stdout (bool): Whether to log to stdout.
        log_level (int): The logging level.
    Returns:
        logging.Logger: The logger instance.
    """
    log_level = log_level or config.log_level
    log_format = logging.Formatter(f'{config.env_name} - %(asctime)s - %(message)s')

    # Log to stdout and to file
    os.makedirs(os.path.dirname(config.log_file), exist_ok=True)
    stdout_handler = logging.StreamHandler(sys.stdout)
    file_handler = TimedRotatingFileHandler(config.log_file, when="midnight", interval=1)
    file_handler.suffix = "%Y%m%d"

    # Set the logger format
    stdout_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)

    # Configure logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    if add_stdout and config.log_stdout:
        logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)
    return logger
