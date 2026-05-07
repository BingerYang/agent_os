"""工具池：从 AgentPublish.config_snapshot 构建 LangChain StructuredTool 并缓存。"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.agents.pool.mcp_pool import MCPConnectionPool

logger = logging.getLogger(__name__)


@dataclass
class ToolPoolEntry:
    """工具池中的单个工具条目。

    Attributes:
        tool_id: 工具 ID。
        lc_tool: 已构建的 LangChain StructuredTool 实例。
        protocol: 工具协议（MCP / HTTP / BUILTIN）。
        mcp_server_endpoint: MCP 工具对应的 Server 端点（非 MCP 工具为 None）。
        loaded_at: 条目加载时间。
    """

    tool_id: int
    lc_tool: Any  # langchain_core.tools.StructuredTool
    protocol: str
    mcp_server_endpoint: str | None = None
    loaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class ToolPool:
    """运行时工具池，从 config_snapshot 构建 LangChain StructuredTool，零数据库读取。

    MCP 工具通过 MCPConnectionPool 复用长连接；HTTP/BUILTIN 工具无状态。

    Usage:
        pool = ToolPool()
        await pool.build_from_snapshot(snapshot["tools"], mcp_pool)
        lc_tools = pool.get_lc_tools([1, 2, 3])
    """

    def __init__(self) -> None:
        self._pool: dict[int, ToolPoolEntry] = {}

    async def build_from_snapshot(
        self,
        snapshot_tools: list[dict],
        mcp_pool: MCPConnectionPool,
    ) -> None:
        """从 config_snapshot 的 tools 字段批量构建并缓存工具。

        对 MCP 工具，尝试从 MCP Server 获取真实 inputSchema 以构建精确的
        args_schema；失败时回退到无 schema 的 StructuredTool。

        Args:
            snapshot_tools: config_snapshot["tools"] 列表。
            mcp_pool: 用于获取 MCP 工具 schema 的连接池。
        """
        # 按端点分组 MCP 工具，批量获取 schema
        mcp_by_endpoint: dict[str, tuple[dict, list[dict]]] = {}
        other_tools: list[dict] = []

        for tool in snapshot_tools:
            protocol = (tool.get("protocol") or "").upper()
            server = tool.get("mcp_server") or {}
            endpoint = server.get("endpoint_url") or tool.get("endpoint_url")
            if protocol == "MCP" and endpoint:
                headers = server.get("headers") or {}
                if endpoint not in mcp_by_endpoint:
                    mcp_by_endpoint[endpoint] = (headers, [])
                mcp_by_endpoint[endpoint][1].append(tool)
            else:
                other_tools.append(tool)

        # 构建非 MCP 工具
        for tool in other_tools:
            entry = self._build_simple_tool(tool)
            self._pool[entry.tool_id] = entry

        # 构建 MCP 工具（获取真实 schema）
        for endpoint, (headers, tools) in mcp_by_endpoint.items():
            try:
                tool_defs = await mcp_pool.get_tool_schemas(endpoint, headers)
                schema_map = {td.name: td for td in tool_defs}
            except Exception as exc:
                logger.warning("tool_pool.schema_fetch_failed endpoint=%s error=%s", endpoint, exc)
                schema_map = {}

            for tool in tools:
                mcp_name = tool.get("mcp_tool_name") or tool.get("name", "")
                tool_def = schema_map.get(mcp_name)
                entry = self._build_mcp_tool(tool, endpoint, headers, tool_def, mcp_pool)
                self._pool[entry.tool_id] = entry

        logger.debug("tool_pool.built count=%d", len(self._pool))

    def get(self, tool_id: int) -> ToolPoolEntry | None:
        """按 ID 查询工具条目。

        Args:
            tool_id: 工具 ID。

        Returns:
            对应的 ToolPoolEntry，不存在时返回 None。
        """
        return self._pool.get(tool_id)

    def get_lc_tools(self, tool_ids: list[int]) -> list[Any]:
        """按 ID 列表返回 LangChain StructuredTool 列表。

        Args:
            tool_ids: 工具 ID 列表。

        Returns:
            对应的 StructuredTool 列表，跳过未找到的 ID。
        """
        result = []
        for tid in tool_ids:
            entry = self._pool.get(tid)
            if entry:
                result.append(entry.lc_tool)
        return result

    def invalidate(self, tool_id: int) -> None:
        """从池中移除指定工具（热更新时使用）。

        Args:
            tool_id: 要移除的工具 ID。
        """
        self._pool.pop(tool_id, None)

    def size(self) -> int:
        """返回当前池中的工具数量。"""
        return len(self._pool)

    # ------------------------------------------------------------------
    # 私有构建方法
    # ------------------------------------------------------------------

    def _build_simple_tool(self, tool: dict) -> ToolPoolEntry:
        """为 HTTP / BUILTIN 工具构建 ToolPoolEntry。"""
        from langchain_core.tools import StructuredTool

        from src.agents.strategies.factory import StrategyFactory

        protocol = (tool.get("protocol") or "HTTP").upper()
        strategy = StrategyFactory.get(protocol)
        tool_config = dict(tool)

        async def _run(**kwargs: Any) -> str:
            try:
                return await strategy.execute(tool_config, kwargs)
            except Exception as exc:
                return f"[ERROR] 工具 {tool.get('name')} 调用失败: {exc}"

        lc_tool = StructuredTool.from_function(
            coroutine=_run,
            name=tool.get("name", "unknown"),
            description=tool.get("description") or tool.get("display_name", ""),
            args_schema=None,
        )
        return ToolPoolEntry(
            tool_id=int(tool["id"]),
            lc_tool=lc_tool,
            protocol=protocol,
        )

    def _build_mcp_tool(
        self,
        tool: dict,
        endpoint: str,
        headers: dict,
        tool_def: Any | None,
        mcp_pool: MCPConnectionPool,
    ) -> ToolPoolEntry:
        """为 MCP 工具构建 ToolPoolEntry（可选携带真实 inputSchema）。"""
        from langchain_core.tools import StructuredTool

        from src.agents.strategies.mcp_strategy import MCPToolStrategy

        strategy = MCPToolStrategy(mcp_pool)
        tool_config = dict(tool)
        tool_config["mcp_server"] = {"endpoint_url": endpoint, "headers": headers}

        description = tool.get("description") or tool.get("display_name", "")
        args_schema = None
        if tool_def is not None:
            description = getattr(tool_def, "description", description) or description
            raw_schema = getattr(tool_def, "inputSchema", None)
            if raw_schema:
                args_schema = _build_args_schema(tool.get("name", "tool"), raw_schema)

        async def _run(**kwargs: Any) -> str:
            try:
                return await strategy.execute(tool_config, kwargs)
            except Exception as exc:
                return f"[ERROR] 工具 {tool.get('name')} 调用失败: {exc}"

        lc_tool = StructuredTool.from_function(
            coroutine=_run,
            name=tool.get("name", "unknown"),
            description=description,
            args_schema=args_schema,
        )
        return ToolPoolEntry(
            tool_id=int(tool["id"]),
            lc_tool=lc_tool,
            protocol="MCP",
            mcp_server_endpoint=endpoint,
        )


# ------------------------------------------------------------------
# 辅助函数：JSON Schema → Pydantic args_schema
# ------------------------------------------------------------------

def _schema_to_python_type(schema: dict[str, Any] | None) -> Any:
    """将 JSON Schema 类型描述转换为 Python 类型注解。"""
    if not isinstance(schema, dict):
        return Any
    if any(k in schema for k in ("anyOf", "oneOf", "allOf")):
        return Any
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        non_null = [t for t in schema_type if t != "null"]
        schema_type = non_null[0] if len(non_null) == 1 else None
    mapping = {"string": str, "integer": int, "number": float, "boolean": bool, "object": dict}
    if schema_type in mapping:
        return mapping[schema_type]
    if schema_type == "array":
        return list[_schema_to_python_type(schema.get("items"))]  # type: ignore[misc]
    return Any


def _build_args_schema(tool_name: str, json_schema: dict[str, Any]) -> Any:
    """根据 MCP inputSchema 构建 Pydantic 模型用于 StructuredTool.args_schema。"""
    from pydantic import Field as PydanticField
    from pydantic import create_model

    properties = json_schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return None
    required = set(json_schema.get("required", []))
    field_defs: dict[str, tuple[Any, Any]] = {}
    for fname, fschema in properties.items():
        if not isinstance(fschema, dict):
            fschema = {}
        annotation = _schema_to_python_type(fschema)
        default = ... if fname in required else fschema.get("default", None)
        field_defs[fname] = (
            annotation,
            PydanticField(default=default, description=fschema.get("description")),
        )
    if not field_defs:
        return None
    model_name = "".join(p.capitalize() for p in re.split(r"[^0-9A-Za-z]+", tool_name) if p) or "Tool"
    return create_model(f"{model_name}Args", **field_defs)  # type: ignore[call-overload]
