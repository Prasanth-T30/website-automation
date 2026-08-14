"""Standard envelope used by every API response for predictable frontend handling."""
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseModel(BaseModel):
    success: bool = True
    message: str = "OK"
    data: Optional[Any] = None


class PaginatedResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: list
    total: int
    page: int
    page_size: int
    total_pages: int
