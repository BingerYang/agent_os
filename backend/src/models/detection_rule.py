import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class DetectionStage(enum.StrEnum):
    PRE = "PRE"
    POST = "POST"


class RuleType(enum.StrEnum):
    KEYWORD = "keyword"
    LLM_JUDGE = "llm_judge"


class DetectionRule(Base):
    __tablename__ = "detection_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    stage: Mapped[DetectionStage] = mapped_column(Enum(DetectionStage), nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(Enum(RuleType), nullable=False)
    rule_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    reject_message: Mapped[str | None] = mapped_column(String(512))
    priority: Mapped[int] = mapped_column(Integer, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
