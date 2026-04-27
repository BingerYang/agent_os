from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    trigger_condition: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSON)
    version: Mapped[str] = mapped_column(String(32), default="v1.0.0")
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    author: Mapped[str] = mapped_column(String(128), nullable=False, default="系统官方")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tools: Mapped[list["Tool"]] = relationship("Tool", secondary="skill_tools", back_populates="skills")  # type: ignore[name-defined]
    agents: Mapped[list["Agent"]] = relationship("Agent", secondary="agent_skills", back_populates="skills")  # type: ignore[name-defined]
