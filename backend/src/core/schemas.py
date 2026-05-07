from datetime import UTC, datetime
from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse[T](BaseModel):
    """统一响应格式（Constitution I）"""
    code: int = 0
    message: str = "success"
    data: T | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def ok(cls, data: T, message: str = "success") -> "ApiResponse[T]":
        return cls(code=0, message=message, data=data)

    @classmethod
    def error(cls, code: int, message: str, data: T | None = None) -> "ApiResponse[T]":
        return cls(code=code, message=message, data=data)


class PageResult[T](BaseModel):
    """分页结果"""
    items: list[T]
    total: int
    page: int
    page_size: int
