import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class MCPTransportType(enum.StrEnum):
    STDIO = "STDIO"
    HTTP_SSE = "HTTP_SSE"


class MCPAuthType(enum.StrEnum):
    NONE = "NONE"
    API_KEY = "API_KEY"
    BEARER_TOKEN = "BEARER_TOKEN"
    BASIC_AUTH = "BASIC_AUTH"
    JWT_BEARER = "JWT_BEARER"
    OAUTH2 = "OAUTH2"


class MCPServerStatus(enum.StrEnum):
    UNKNOWN = "UNKNOWN"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    transport_type: Mapped[MCPTransportType] = mapped_column(Enum(MCPTransportType), nullable=False, default=MCPTransportType.HTTP_SSE)
    command: Mapped[str | None] = mapped_column(String(512))
    args: Mapped[list | None] = mapped_column(JSON)
    # env_vars 加密存储：{"KEY": "value"} 形式，通过 AES-256-GCM 加密
    env_vars: Mapped[dict | None] = mapped_column(JSON)
    endpoint_url: Mapped[str | None] = mapped_column(String(512))
    auth_type: Mapped[MCPAuthType] = mapped_column(Enum(MCPAuthType), nullable=False, default=MCPAuthType.NONE)
    # auth_config 结构：API_KEY: {key_name, key_value, key_location(header/query)}; BEARER_TOKEN: {token}; BASIC_AUTH: {username, password}
    auth_config: Mapped[dict | None] = mapped_column(JSON)
    # headers：自定义请求头键值对，在认证头之后追加/覆盖
    headers: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[MCPServerStatus] = mapped_column(Enum(MCPServerStatus), nullable=False, default=MCPServerStatus.UNKNOWN)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    tools: Mapped[list["Tool"]] = relationship("Tool", back_populates="mcp_server", cascade="all, delete-orphan")  # type: ignore[name-defined]
