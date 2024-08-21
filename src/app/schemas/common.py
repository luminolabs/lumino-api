from pydantic import BaseModel


class Pagination(BaseModel):
    total_pages: int
    current_page: int
    items_per_page: int
