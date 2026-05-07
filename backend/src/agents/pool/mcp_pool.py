"""MCP 长连接池：每个 Server 端点维护一个 ClientSession，asyncio.Lock 串行化调用。"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MCPEntry:
    """单个 MCP Server 端点的连接条目。

    Attributes:
        endpoint_url: MCP Server 的完整 URL。
        headers: 认证请求头（Bearer / API-Key 等）。
        session: 已建立的 ClientSession；None 表示尚未连接。
        lock: asyncio.Lock，保证对此端点的工具调用串行执行。
        connected_at: 最近一次连接建立时间。
        last_used_at: 最近一次工具调用时间。
        is_healthy: 连接是否健康；False 时下次调用前触发重连。
        _http_client: 内部保持的 httpx.AsyncClient（生命周期随连接）。
        _transport_ctx: streamable_http_client 上下文管理器句柄。
        _session_ctx: ClientSession 上下文管理器句柄。
    """

    endpoint_url: str
    headers: dict[str, str] = field(default_factory=dict)
    session: Any | None = None  # mcp.ClientSession
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    connected_at: datetime | None = None
    last_used_at: datetime | None = None
    is_healthy: bool = True
    _http_client: Any | None = None
    _transport_ctx: Any | None = None
    _session_ctx: Any | None = None


class MCPConnectionPool:
    """MCP Server 长连接池。

    每个唯一 endpoint_url 维护一个 MCPEntry（单连接）。
    所有对同一端点的工具调用通过 MCPEntry.lock 串行化，避免并发混淆。

    Usage:
        pool = MCPConnectionPool()
        result = await pool.call_tool("http://mcp-server/mcp", "get_weather", {"city": "北京"})
    """

    def __init__(self) -> None:
        self._entries: dict[str, MCPEntry] = {}

    def get_or_create(
        self,
        endpoint_url: str,
        headers: dict[str, str] | None = None,
    ) -> MCPEntry:
        """获取或新建端点的连接条目（同步）。

        Args:
            endpoint_url: MCP Server 端点 URL。
            headers: 可选的认证请求头。

        Returns:
            对应端点的 MCPEntry。
        """
        if endpoint_url not in self._entries:
            self._entries[endpoint_url] = MCPEntry(
                endpoint_url=endpoint_url,
                headers=headers or {},
            )
        return self._entries[endpoint_url]

    async def ensure_connected(self, entry: MCPEntry) -> None:
        """确保 entry 已建立有效连接；必要时重连（在 lock 保护内执行）。

        Args:
            entry: 需要确认连接状态的 MCPEntry。

        Raises:
            Exception: 连接失败时向上抛出，同时将 is_healthy 置为 False。
        """
        if entry.session is not None and entry.is_healthy:
            return

        async with entry.lock:
            # 双重检查：其他协程可能已完成重连
            if entry.session is not None and entry.is_healthy:
                return

            # 先清理旧连接
            await self._close_entry(entry)

            try:
                import httpx
                from mcp import ClientSession
                from mcp.client.streamable_http import streamable_http_client

                http_client = httpx.AsyncClient(timeout=30.0, headers=entry.headers)
                transport_ctx = streamable_http_client(entry.endpoint_url, http_client=http_client)
                read_stream, write_stream, _ = await transport_ctx.__aenter__()
                session_ctx = ClientSession(read_stream, write_stream)
                session = await session_ctx.__aenter__()
                await session.initialize()

                entry._http_client = http_client
                entry._transport_ctx = transport_ctx
                entry._session_ctx = session_ctx
                entry.session = session
                entry.is_healthy = True
                entry.connected_at = datetime.now(UTC)
                logger.info("mcp_pool.connected endpoint=%s", entry.endpoint_url)

            except Exception as exc:
                entry.is_healthy = False
                logger.error("mcp_pool.connect_failed endpoint=%s error=%s", entry.endpoint_url, exc)
                raise

    async def call_tool(
        self,
        endpoint_url: str,
        tool_name: str,
        args: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> str:
        """通过连接池调用 MCP 工具（串行化）。

        Args:
            endpoint_url: MCP Server 端点 URL。
            tool_name: MCP 工具名称。
            args: 工具调用参数。
            headers: 可选的认证请求头（首次创建条目时使用）。

        Returns:
            工具返回内容的字符串表示，多段以换行拼接；空结果返回"[工具返回空结果]"。

        Raises:
            Exception: 工具调用失败时向上抛出。
        """
        entry = self.get_or_create(endpoint_url, headers)
        await self.ensure_connected(entry)

        async with entry.lock:
            entry.last_used_at = datetime.now(UTC)
            try:
                result = await entry.session.call_tool(tool_name, arguments=args)  # type: ignore[union-attr]
            except Exception as exc:
                entry.is_healthy = False
                logger.error(
                    "mcp_pool.call_tool_failed endpoint=%s tool=%s error=%s",
                    endpoint_url, tool_name, exc,
                )
                raise

        parts: list[str] = []
        for item in result.content:
            if hasattr(item, "text"):
                parts.append(item.text)
            elif isinstance(item, dict):
                import json
                parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return "\n".join(parts) or "[工具返回空结果]"

    async def get_tool_schemas(
        self,
        endpoint_url: str,
        headers: dict[str, str] | None = None,
    ) -> list[Any]:
        """获取指定端点的工具定义列表（用于构建 args_schema）。

        Args:
            endpoint_url: MCP Server 端点 URL。
            headers: 可选的认证请求头。

        Returns:
            mcp.types.Tool 对象列表。
        """
        entry = self.get_or_create(endpoint_url, headers)
        await self.ensure_connected(entry)

        async with entry.lock:
            result = await entry.session.list_tools()  # type: ignore[union-attr]
        return result.tools

    async def close_all(self) -> None:
        """关闭所有 MCP 连接，释放资源。"""
        for endpoint_url, entry in list(self._entries.items()):
            await self._close_entry(entry)
            logger.info("mcp_pool.closed endpoint=%s", endpoint_url)
        self._entries.clear()

    @staticmethod
    async def _close_entry(entry: MCPEntry) -> None:
        """关闭单个条目的连接，忽略关闭时的错误。"""
        entry.session = None
        entry.is_healthy = False

        for attr in ("_session_ctx", "_transport_ctx", "_http_client"):
            ctx = getattr(entry, attr, None)
            if ctx is None:
                continue
            try:
                if hasattr(ctx, "__aexit__"):
                    await ctx.__aexit__(None, None, None)
                elif hasattr(ctx, "aclose"):
                    await ctx.aclose()
            except Exception as exc:
                logger.warning("mcp_pool.close_error attr=%s error=%s", attr, exc)
            finally:
                setattr(entry, attr, None)
