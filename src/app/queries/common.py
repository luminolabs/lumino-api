from typing import Tuple, List

from sqlalchemy import Select, select, func, Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.core.utils import T
from app.schemas.common import Pagination


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
    # Validate inputs
    if page < 1 or items_per_page < 1:
        raise BadRequestError("`page` and `items_per_page` must be positive integers")

    # Count total items
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)

    # Calculate total pages and validate if page is out of range
    total_pages = (total_count + items_per_page - 1) // items_per_page
    if page > total_pages:
        return [], Pagination(
            total_pages=total_pages,
            current_page=page,
            items_per_page=items_per_page,
        )

    offset = (page - 1) * items_per_page

    # Fetch items
    result = await db.execute(query.offset(offset).limit(items_per_page))
    items = result.all()

    if items and isinstance(items[0], Row) and len(items[0]) == 1:
        items = [item[0] for item in items]

    # Create pagination object
    pagination = Pagination(
        total_pages=total_pages,
        current_page=page,
        items_per_page=items_per_page,
    )

    # Return items and pagination
    return items, pagination
