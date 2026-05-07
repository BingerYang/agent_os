from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class LLMModel(Base):
    __tablename__ = "llm_models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_id: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    supplier: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(String(512))
    api_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    api_version: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
