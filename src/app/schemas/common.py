from pydantic import BaseModel


class Pagination(BaseModel):
    """
    Schema for pagination information. Used to provide pagination details in API responses.
    """
    total_pages: int
    current_page: int
    items_per_page: int
