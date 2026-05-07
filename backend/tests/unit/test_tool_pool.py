"""T025: TDD 单元测试 - ToolPool。"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from langchain_core.tools import StructuredTool

from src.agents.pool.tool_pool import ToolPool


@pytest.fixture
def mcp_pool():
    mock = MagicMock()
    mock.get_tool_schemas = AsyncMock(return_value=[])
    return mock


@pytest.mark.asyncio
async def test_build_from_snapshot_http_tool(mcp_pool):
    """HTTP 工具从 snapshot 构建 StructuredTool 并入池。"""
    pool = ToolPool()
    snapshot = [
        {
            "id": 1,
            "name": "http_tool",
            "description": "A test HTTP tool",
            "protocol": "HTTP",
            "endpoint_url": "http://example.com/tool",
        }
    ]
    await pool.build_from_snapshot(snapshot, mcp_pool)
    assert pool.size() == 1
    entry = pool.get(1)
    assert entry is not None
    assert entry.protocol == "HTTP"
    assert isinstance(entry.lc_tool, StructuredTool)


@pytest.mark.asyncio
async def test_build_from_snapshot_mcp_tool_uses_strategy(mcp_pool):
    """MCP 工具构建时调用 mcp_pool.get_tool_schemas 获取真实 schema。"""
    tool_def = MagicMock()
    tool_def.name = "search"
    tool_def.description = "Search tool"
    tool_def.inputSchema = {
        "type": "object",
        "properties": {"q": {"type": "string"}},
        "required": ["q"],
    }
    mcp_pool.get_tool_schemas = AsyncMock(return_value=[tool_def])

    pool = ToolPool()
    snapshot = [
        {
            "id": 2,
            "name": "search",
            "mcp_tool_name": "search",
            "description": "Search",
            "protocol": "MCP",
            "mcp_server": {
                "endpoint_url": "http://mcp-server/mcp",
                "headers": {},
            },
        }
    ]
    await pool.build_from_snapshot(snapshot, mcp_pool)
    mcp_pool.get_tool_schemas.assert_called_once_with("http://mcp-server/mcp", {})
    entry = pool.get(2)
    assert entry is not None
    assert entry.protocol == "MCP"
    assert entry.mcp_server_endpoint == "http://mcp-server/mcp"


@pytest.mark.asyncio
async def test_get_lc_tools_returns_correct_subset(mcp_pool):
    """get_lc_tools 只返回指定 ID 对应的工具。"""
    pool = ToolPool()
    snapshot = [
        {"id": 1, "name": "tool_a", "description": "A", "protocol": "HTTP"},
        {"id": 2, "name": "tool_b", "description": "B", "protocol": "HTTP"},
        {"id": 3, "name": "tool_c", "description": "C", "protocol": "HTTP"},
    ]
    await pool.build_from_snapshot(snapshot, mcp_pool)
    lc = pool.get_lc_tools([1, 3])
    assert len(lc) == 2
    names = {t.name for t in lc}
    assert names == {"tool_a", "tool_c"}


@pytest.mark.asyncio
async def test_invalidate_removes_tool(mcp_pool):
    """invalidate 从池中移除指定工具。"""
    pool = ToolPool()
    snapshot = [{"id": 1, "name": "tool_a", "description": "A", "protocol": "HTTP"}]
    await pool.build_from_snapshot(snapshot, mcp_pool)
    assert pool.size() == 1
    pool.invalidate(1)
    assert pool.size() == 0
    assert pool.get(1) is None


@pytest.mark.asyncio
async def test_mcp_schema_fetch_failure_falls_back(mcp_pool):
    """MCP schema 拉取失败时工具仍然入池（无 args_schema）。"""
    mcp_pool.get_tool_schemas = AsyncMock(side_effect=Exception("connection refused"))
    pool = ToolPool()
    snapshot = [
        {
            "id": 5,
            "name": "mcp_tool",
            "description": "MCP fallback test",
            "protocol": "MCP",
            "mcp_server": {"endpoint_url": "http://mcp/mcp", "headers": {}},
        }
    ]
    await pool.build_from_snapshot(snapshot, mcp_pool)
    # schema 拉取失败时工具仍然入池且可调用
    assert pool.size() == 1
    entry = pool.get(5)
    assert entry is not None
    assert isinstance(entry.lc_tool, StructuredTool)
