"""Query parameters and response body shared by all paginated listings."""

from pydantic import BaseModel, Field


class PageParams(BaseModel):
    """Use in an endpoint as ``params: Annotated[PageParams, Query()]``."""

    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page[ItemT](BaseModel):
    items: list[ItemT]
    total: int
    page: int
    size: int
