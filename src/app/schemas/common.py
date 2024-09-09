from functools import partial

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    """
    Schema for pagination information. Used to provide pagination details in API responses.
    """
    total_pages: int
    current_page: int
    items_per_page: int


NameField = partial(Field, ...,
                    min_length=1, max_length=255,
                    pattern="^[a-z0-9-]+$")