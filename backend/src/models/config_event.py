from datetime import datetime, timezone
import enum
from sqlalchemy import BigInteger, DateTime, Enum, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class ObjectType(str, enum.Enum):
    AGENT = "agent"
    TOOL = "tool"
    SKILL = "skill"
    PIPELINE = "pipeline"
    DETECTION_RULE = "detection_rule"
    LLM_MODEL = "llm_model"


class ConfigChangeEvent(Base):
    __tablename__ = "config_change_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_type: Mapped[ObjectType] = mapped_column(Enum(ObjectType), nullable=False)
    object_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    change_summary: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
