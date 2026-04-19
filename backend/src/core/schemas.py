from datetime import datetime, timezone
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应格式（Constitution I）"""
    code: int = 0
    message: str = "success"
    data: T | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def ok(cls, data: T, message: str = "success") -> "ApiResponse[T]":
        return cls(code=0, message=message, data=data)

    @classmethod
    def error(cls, code: int, message: str, data: T | None = None) -> "ApiResponse[T]":
        return cls(code=code, message=message, data=data)


class PageResult(BaseModel, Generic[T]):
    """分页结果"""
    items: list[T]
    total: int
    page: int
    page_size: int
