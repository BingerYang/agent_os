import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class AgentType(enum.StrEnum):
    SINGLE = "SINGLE"
    SUB = "SUB"
    ORCHESTRATOR = "ORCHESTRATOR"
    THIRD_PARTY = "THIRD_PARTY"


class AgentStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False, default=AgentType.SINGLE)
    source_platform: Mapped[str] = mapped_column(String(128), default="local")
    access_url: Mapped[str | None] = mapped_column(String(512))
    access_token: Mapped[str | None] = mapped_column(String(1024))
    llm_model_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("llm_models.id"))
    system_prompt: Mapped[str | None] = mapped_column(Text)
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), nullable=False, default=AgentStatus.DRAFT)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=2048)
    # 意图识别配置（仅 SINGLE 类型使用）
    intent_recognition_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    intent_model_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("llm_models.id"))
    intent_confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    intent_system_prompt: Mapped[str | None] = mapped_column(Text)
    intent_entity_schema: Mapped[list | None] = mapped_column(JSON)
    # 路由配置（仅 ORCHESTRATOR 类型使用）
    routing_strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="smart")
    routing_model_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("llm_models.id"))
    routing_system_prompt: Mapped[str | None] = mapped_column(Text)
    routing_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    routing_intent_rules: Mapped[list | None] = mapped_column(JSON)
    sub_agent_ids: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 发布状态（由发布服务维护）
    published_version: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    last_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    llm_model: Mapped["LLMModel | None"] = relationship("LLMModel", foreign_keys=[llm_model_id])  # type: ignore[name-defined]
    tools: Mapped[list["Tool"]] = relationship("Tool", secondary="agent_tools", back_populates="agents")  # type: ignore[name-defined]
    skills: Mapped[list["Skill"]] = relationship("Skill", secondary="agent_skills", back_populates="agents")  # type: ignore[name-defined]
