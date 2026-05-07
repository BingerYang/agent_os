"""T030: TDD 集成测试 - MultiAgentNode 单路由真实流式 vs 多路由批量推送。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentContext, StreamEvent
from src.agents.multi_agent import MultiAgentNode
from src.agents.single_agent import SingleAgentNode
from src.runtime.context import PipelineCacheEntry


def _make_context(sub_agent_ids: list[int]) -> AgentContext:
    """构建包含指定子 Agent 的 AgentContext mock。"""
    pipeline_cfg = PipelineCacheEntry(
        pipeline_uid="pl-multi",
        pipeline_id=1,
        pipeline_type="MULTI_AGENT",
        primary_agent_id=100,
    )
    orchestrator = MagicMock()
    orchestrator.agent_id = 100
    orchestrator.sub_agent_ids = sub_agent_ids
    orchestrator.system_prompt = "orchestrator"
    orchestrator.route_confidence_threshold = 0.7
    orchestrator.timeout_seconds = 30

    sub_pool: dict[int, MagicMock] = {}
    for sid in sub_agent_ids:
        entry = MagicMock()
        entry.agent_id = sid
        entry.system_prompt = f"sub agent {sid}"
        entry.compiled_graph = MagicMock()
        msg = MagicMock()
        msg.content = f"answer from {sid}"
        msg.tool_calls = []
        entry.compiled_graph.ainvoke = AsyncMock(return_value={"messages": [msg]})
        sub_pool[sid] = entry

    def pool_get(agent_id: int):
        if agent_id == 100:
            return orchestrator
        return sub_pool.get(agent_id)

    pool = MagicMock()
    pool.get = pool_get

    return AgentContext(
        query="test query",
        session_id="sess-stream",
        pipeline_config=pipeline_cfg,
        agent_pool=pool,
        tool_pool=MagicMock(),
        mcp_pool=MagicMock(),
    )


@pytest.mark.asyncio
async def test_single_sub_agent_delegates_to_single_node_stream():
    """只有一个子 Agent 时，stream() 委托给 SingleAgentNode.stream()，实现真实流式。"""
    context = _make_context(sub_agent_ids=[10])

    async def mock_stream(self, ctx):
        yield StreamEvent(type="answer", content="token1")
        yield StreamEvent(type="answer", content="token2")
        yield StreamEvent(
            type="__done__",
            answer="token1token2",
            tools_called=[],
            session_id="sess-stream",
            latency_ms=50,
        )

    with patch.object(SingleAgentNode, "stream", mock_stream):
        node = MultiAgentNode()
        events = [e async for e in node.stream(context)]

    types = [e.type for e in events]
    assert types.count("answer") == 2
    assert types[-1] == "__done__"


@pytest.mark.asyncio
async def test_multi_sub_agents_batch_yields_answer_and_done():
    """多个子 Agent 时，batch 执行后推送 answer 和 __done__ 事件。"""
    context = _make_context(sub_agent_ids=[10, 20])

    node = MultiAgentNode()
    events = [e async for e in node.stream(context)]

    types = [e.type for e in events]
    assert "answer" in types
    assert "__done__" in types
    assert "__error__" not in types


@pytest.mark.asyncio
async def test_stream_done_event_contains_session_id():
    """__done__ 事件必须携带 session_id。"""
    context = _make_context(sub_agent_ids=[10, 20])

    node = MultiAgentNode()
    done_events = [e async for e in node.stream(context) if e.type == "__done__"]

    assert len(done_events) == 1
    assert done_events[0].session_id == "sess-stream"


@pytest.mark.asyncio
async def test_no_sub_agents_returns_terminal_event():
    """没有子 Agent 时，stream() 返回终止事件，不挂起。"""
    context = _make_context(sub_agent_ids=[])

    node = MultiAgentNode()
    events = [e async for e in node.stream(context)]

    assert len(events) >= 1
    assert events[-1].type in ("__done__", "__error__", "answer")
