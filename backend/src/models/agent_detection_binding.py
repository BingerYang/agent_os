from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class AgentDetectionBinding(Base):
    """Agent 与 DetectionRule 的绑定关系，支持 per-agent 配置覆盖。"""
    __tablename__ = "agent_detection_bindings"
    __table_args__ = (
        UniqueConstraint("agent_id", "rule_id", name="uq_agent_rule"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[int] = mapped_column(
        ForeignKey("detection_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_override: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    action_override: Mapped[str | None] = mapped_column(String(32), nullable=True)
    priority_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
