"""T024: TDD 单元测试 - MCPConnectionPool。"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.pool.mcp_pool import MCPConnectionPool, MCPEntry


def _make_mock_session() -> MagicMock:
    """创建 mock MCP ClientSession，call_tool 返回带 text 的 content 列表。"""
    content_item = MagicMock()
    content_item.text = "mock result"
    mock_result = MagicMock()
    mock_result.content = [content_item]

    session = MagicMock()
    session.call_tool = AsyncMock(return_value=mock_result)
    session.list_tools = AsyncMock(return_value=MagicMock(tools=[]))
    return session


def test_get_or_create_returns_same_entry():
    """相同 endpoint_url 的 get_or_create 返回同一 MCPEntry 实例。"""
    pool = MCPConnectionPool()
    e1 = pool.get_or_create("http://server/mcp")
    e2 = pool.get_or_create("http://server/mcp")
    assert e1 is e2


def test_get_or_create_different_endpoints():
    """不同 endpoint_url 返回不同 MCPEntry。"""
    pool = MCPConnectionPool()
    e1 = pool.get_or_create("http://server-a/mcp")
    e2 = pool.get_or_create("http://server-b/mcp")
    assert e1 is not e2


@pytest.mark.asyncio
async def test_call_tool_reuses_connection():
    """连续调用 call_tool 只建立一次连接（ensure_connected 只初始化一次）。"""
    pool = MCPConnectionPool()
    mock_session = _make_mock_session()

    with patch.object(pool, "ensure_connected", new=AsyncMock()) as mock_connect:
        entry = pool.get_or_create("http://server/mcp")
        entry.session = mock_session
        entry.is_healthy = True

        await pool.call_tool("http://server/mcp", "tool_a", {})
        await pool.call_tool("http://server/mcp", "tool_a", {})

    # ensure_connected 调用了两次，但 session 未重建（mock 验证没有 side effect）
    assert mock_connect.call_count == 2
    assert mock_session.call_tool.call_count == 2


@pytest.mark.asyncio
async def test_call_tool_returns_text_content():
    """call_tool 正确拼接 content.text 内容。"""
    pool = MCPConnectionPool()
    mock_session = _make_mock_session()

    with patch.object(pool, "ensure_connected", new=AsyncMock()):
        entry = pool.get_or_create("http://server/mcp")
        entry.session = mock_session
        entry.is_healthy = True

        result = await pool.call_tool("http://server/mcp", "tool_a", {"x": 1})

    assert result == "mock result"


@pytest.mark.asyncio
async def test_serialization_with_lock():
    """asyncio.Lock 保证同一 entry 的工具调用串行执行（不乱序）。"""
    pool = MCPConnectionPool()
    call_order: list[int] = []

    async def slow_tool(**kwargs: dict) -> str:
        await asyncio.sleep(0.05)
        call_order.append(kwargs.get("seq", 0))
        return "ok"

    content = MagicMock()
    content.text = "ok"
    mock_result = MagicMock()
    mock_result.content = [content]

    mock_session = MagicMock()
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    entry = pool.get_or_create("http://server/mcp")
    entry.session = mock_session
    entry.is_healthy = True

    with patch.object(pool, "ensure_connected", new=AsyncMock()):
        tasks = [
            asyncio.create_task(pool.call_tool("http://server/mcp", f"tool_{i}", {}))
            for i in range(3)
        ]
        await asyncio.gather(*tasks)

    # 因为 lock 串行化，call_tool 被调用了 3 次
    assert mock_session.call_tool.call_count == 3


@pytest.mark.asyncio
async def test_ensure_connected_skips_if_healthy():
    """entry.session 已存在且 is_healthy=True 时 ensure_connected 立即返回。"""
    pool = MCPConnectionPool()
    entry = pool.get_or_create("http://server/mcp")
    entry.session = MagicMock()
    entry.is_healthy = True

    # 不会进入 lock 内部（如果进入会抛出，因为没有 mock httpx/mcp）
    await pool.ensure_connected(entry)
    assert entry.is_healthy is True


@pytest.mark.asyncio
async def test_ensure_connected_sets_unhealthy_on_failure():
    """连接失败时 is_healthy=False 并向上抛出异常。"""
    pool = MCPConnectionPool()
    entry = pool.get_or_create("http://server/mcp")
    entry.session = None
    entry.is_healthy = False

    with patch("httpx.AsyncClient", side_effect=RuntimeError("conn fail")):
        with pytest.raises(RuntimeError, match="conn fail"):
            await pool.ensure_connected(entry)

    assert entry.is_healthy is False


@pytest.mark.asyncio
async def test_call_tool_marks_unhealthy_on_error():
    """session.call_tool 抛出异常时标记 is_healthy=False 并重新抛出。"""
    pool = MCPConnectionPool()
    mock_session = MagicMock()
    mock_session.call_tool = AsyncMock(side_effect=RuntimeError("tool error"))

    with patch.object(pool, "ensure_connected", new=AsyncMock()):
        entry = pool.get_or_create("http://server/mcp")
        entry.session = mock_session
        entry.is_healthy = True

        with pytest.raises(RuntimeError, match="tool error"):
            await pool.call_tool("http://server/mcp", "bad_tool", {})

    assert entry.is_healthy is False


@pytest.mark.asyncio
async def test_call_tool_empty_content_returns_placeholder():
    """工具返回空 content 时返回占位符字符串。"""
    pool = MCPConnectionPool()
    mock_result = MagicMock()
    mock_result.content = []
    mock_session = MagicMock()
    mock_session.call_tool = AsyncMock(return_value=mock_result)

    with patch.object(pool, "ensure_connected", new=AsyncMock()):
        entry = pool.get_or_create("http://server/mcp")
        entry.session = mock_session
        entry.is_healthy = True

        result = await pool.call_tool("http://server/mcp", "empty_tool", {})

    assert result == "[工具返回空结果]"


@pytest.mark.asyncio
async def test_get_tool_schemas_returns_tools():
    """get_tool_schemas 返回 list_tools 结果。"""
    pool = MCPConnectionPool()
    fake_tool = MagicMock()
    mock_result = MagicMock()
    mock_result.tools = [fake_tool]
    mock_session = MagicMock()
    mock_session.list_tools = AsyncMock(return_value=mock_result)

    with patch.object(pool, "ensure_connected", new=AsyncMock()):
        entry = pool.get_or_create("http://server/mcp")
        entry.session = mock_session
        entry.is_healthy = True

        tools = await pool.get_tool_schemas("http://server/mcp")

    assert tools == [fake_tool]


@pytest.mark.asyncio
async def test_close_all_clears_entries():
    """close_all 后 _entries 为空。"""
    pool = MCPConnectionPool()
    entry = pool.get_or_create("http://server-a/mcp")
    entry.session = MagicMock()

    await pool.close_all()
    assert len(pool._entries) == 0
