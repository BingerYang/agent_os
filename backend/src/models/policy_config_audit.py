import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ChangeType(enum.StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"
    BIND = "BIND"
    UNBIND = "UNBIND"


class PolicyConfigAudit(Base):
    """策略配置变更的操作审计记录。"""
    __tablename__ = "policy_config_audits"
    __table_args__ = (
        Index("idx_pca_rule_id", "rule_id"),
        Index("idx_pca_agent_id", "agent_id"),
        Index("idx_pca_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    operator_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule_id: Mapped[int] = mapped_column(Integer, nullable=False)
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    before_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
