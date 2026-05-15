import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class EventStatus(enum.StrEnum):
    LOGGED = "LOGGED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REVIEWED = "REVIEWED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"


class DetectionEvent(Base):
    """策略命中审计日志，兼做 Review Queue 和 Escalation Queue。"""
    __tablename__ = "detection_events"
    __table_args__ = (
        Index("idx_de_agent_id", "agent_id"),
        Index("idx_de_rule_id", "rule_id"),
        Index("idx_de_status", "status"),
        Index("idx_de_created_at", "created_at"),
        Index("idx_de_strategy_type", "strategy_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("detection_rules.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stage: Mapped[str] = mapped_column(String(8), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(32), nullable=False)
    action_taken: Mapped[str] = mapped_column(String(32), nullable=False)
    hit_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    input_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=EventStatus.LOGGED)
    reviewer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
