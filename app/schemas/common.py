from typing import Literal

from pydantic import BaseModel, Field

from app.utils.misc import get_utc_iso_now


class PaginationData(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class APIResponse[T](BaseModel):
    status: Literal["success", "error"] = "success"
    data: T | None = None
    message: str | None = None
    timestamp: str = Field(default_factory=get_utc_iso_now)

    pagination: PaginationData | None = None


class PaginatedResponse[T](APIResponse[T]):
    """API response format for paginated results."""

    data: T | None = None
    pagination: PaginationData  # pyright: ignore[reportGeneralTypeIssues]
