import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class ToolProtocol(enum.StrEnum):
    MCP = "MCP"
    HTTP = "HTTP"
    BUILTIN = "BUILTIN"


class ToolAuthType(enum.StrEnum):
    NONE = "NONE"
    API_KEY = "API_KEY"
    BEARER_TOKEN = "BEARER_TOKEN"
    BASIC_AUTH = "BASIC_AUTH"
    JWT_BEARER = "JWT_BEARER"
    OAUTH2 = "OAUTH2"


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    protocol: Mapped[ToolProtocol] = mapped_column(Enum(ToolProtocol), nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(String(512))
    auth_type: Mapped[ToolAuthType] = mapped_column(Enum(ToolAuthType), nullable=False, default=ToolAuthType.NONE)
    # API_KEY: {key_name, key_value, key_location(header/query)}
    # BEARER_TOKEN: {token}
    # BASIC_AUTH: {username, password}
    # JWT_BEARER: {token}
    # OAUTH2: {access_token, token_type}
    auth_config: Mapped[dict | None] = mapped_column(JSON)
    headers: Mapped[dict | None] = mapped_column(JSON)
    mcp_server_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("mcp_servers.id", ondelete="SET NULL"))
    mcp_tool_name: Mapped[str | None] = mapped_column(String(128))
    input_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_schema: Mapped[dict | None] = mapped_column(JSON)
    source_platform: Mapped[str] = mapped_column(String(128), default="local")
    tags: Mapped[list | None] = mapped_column(JSON)
    version: Mapped[str] = mapped_column(String(32), default="v1.0.0")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    agents: Mapped[list["Agent"]] = relationship("Agent", secondary="agent_tools", back_populates="tools")  # type: ignore[name-defined]
    skills: Mapped[list["Skill"]] = relationship("Skill", secondary="skill_tools", back_populates="tools")  # type: ignore[name-defined]
    mcp_server: Mapped["MCPServer | None"] = relationship("MCPServer", back_populates="tools")  # type: ignore[name-defined]
