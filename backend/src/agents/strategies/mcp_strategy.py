"""MCP 协议工具调用策略：通过 MCPConnectionPool 复用长连接。"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.agents.strategies.base import BaseToolStrategy

if TYPE_CHECKING:
    from src.agents.pool.mcp_pool import MCPConnectionPool


class MCPToolStrategy(BaseToolStrategy):
    """MCP 协议工具策略，调用通过连接池串行化。

    Args:
        mcp_pool: 运行时共享的 MCPConnectionPool 实例。
    """

    def __init__(self, mcp_pool: MCPConnectionPool) -> None:
        self._pool = mcp_pool

    async def execute(self, tool_config: dict[str, Any], kwargs: dict[str, Any]) -> str:
        """通过 MCPConnectionPool 调用 MCP 工具。

        Args:
            tool_config: 工具配置，需包含 mcp_server.endpoint_url、
                mcp_server.headers（可选）、mcp_tool_name 字段。
            kwargs: 工具调用参数。

        Returns:
            工具返回内容的字符串。
        """
        server = tool_config.get("mcp_server") or {}
        endpoint_url: str = server.get("endpoint_url") or tool_config.get("endpoint_url", "")
        headers: dict[str, str] = server.get("headers") or {}
        tool_name: str = tool_config.get("mcp_tool_name") or tool_config.get("name", "")

        return await self._pool.call_tool(endpoint_url, tool_name, kwargs, headers)
