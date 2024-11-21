from datetime import datetime
from functools import partial
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer


class Pagination(BaseModel):
    """
    Schema for pagination information. Used to provide pagination details in API responses.
    """
    total_pages: int
    current_page: int
    items_per_page: int


NameField = partial(Field,
                    min_length=1, max_length=255,
                    pattern="^[a-z0-9-]+$")

DateTime = Annotated[
    datetime,
    PlainSerializer(lambda _datetime: _datetime.strftime("%Y-%m-%dT%H:%M:%SZ"), return_type=str),
]
