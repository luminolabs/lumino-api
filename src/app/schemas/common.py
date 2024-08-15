from pydantic import BaseModel


NAME_REGEX_LABEL = 'Must contain only lowercase letters, numbers, underscores, and hyphens.'


class Pagination(BaseModel):
    total_pages: int
    current_page: int
    items_per_page: int
    next_page: int | None
    previous_page: int | None
