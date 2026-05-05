from datetime import datetime, timezone
import enum
import uuid as _uuid_lib
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


class PipelineType(str, enum.Enum):
    SINGLE_AGENT = "SINGLE_AGENT"
    MULTI_AGENT = "MULTI_AGENT"


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False,
        default=lambda: str(_uuid_lib.uuid4())
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    pipeline_type: Mapped[PipelineType] = mapped_column(Enum(PipelineType), nullable=False)
    primary_agent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("agents.id"))
    route_confidence_threshold: Mapped[float] = mapped_column(Float, default=0.7)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    stream_output: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    primary_agent: Mapped["Agent | None"] = relationship("Agent", foreign_keys=[primary_agent_id])  # type: ignore[name-defined]
    detection_rules: Mapped[list["DetectionRule"]] = relationship("DetectionRule", secondary="pipeline_detection_rules")  # type: ignore[name-defined]
