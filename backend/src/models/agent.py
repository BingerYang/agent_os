from datetime import datetime, timezone
import enum
from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


class AgentType(str, enum.Enum):
    SINGLE = "SINGLE"
    SUB = "SUB"
    ORCHESTRATOR = "ORCHESTRATOR"
    THIRD_PARTY = "THIRD_PARTY"


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
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    llm_model: Mapped["LLMModel | None"] = relationship("LLMModel")  # type: ignore[name-defined]
    tools: Mapped[list["Tool"]] = relationship("Tool", secondary="agent_tools", back_populates="agents")  # type: ignore[name-defined]
    skills: Mapped[list["Skill"]] = relationship("Skill", secondary="agent_skills", back_populates="agents")  # type: ignore[name-defined]
