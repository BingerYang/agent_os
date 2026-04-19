from datetime import datetime, timezone
import enum
from sqlalchemy import Boolean, DateTime, Enum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class DetectionStage(str, enum.Enum):
    PRE = "PRE"
    POST = "POST"


class RuleType(str, enum.Enum):
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
