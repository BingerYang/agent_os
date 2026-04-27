from datetime import datetime, timezone
import enum
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


class AgentType(str, enum.Enum):
    SINGLE = "SINGLE"
    SUB = "SUB"
    ORCHESTRATOR = "ORCHESTRATOR"
    THIRD_PARTY = "THIRD_PARTY"


class AgentStatus(str, enum.Enum):
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
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    llm_model: Mapped["LLMModel | None"] = relationship("LLMModel", foreign_keys=[llm_model_id])  # type: ignore[name-defined]
    tools: Mapped[list["Tool"]] = relationship("Tool", secondary="agent_tools", back_populates="agents")  # type: ignore[name-defined]
    skills: Mapped[list["Skill"]] = relationship("Skill", secondary="agent_skills", back_populates="agents")  # type: ignore[name-defined]
