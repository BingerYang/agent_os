"""单元测试 - query_service（RuntimeContext 版本）。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import AgentResult
from src.core.exceptions import PreCheckRejected
from src.runtime.context import PipelineCacheEntry, RuntimeContext
from src.services.query_service import execute_query


def _make_context(pipeline_type: str = "SINGLE_AGENT") -> RuntimeContext:
    """构建最小化 RuntimeContext mock。"""
    pipeline_cfg = PipelineCacheEntry(
        pipeline_uid="pl-001",
        pipeline_id=1,
        pipeline_type=pipeline_type,
        primary_agent_id=10,
        detection_rule_ids=[],
        enabled=True,
    )
    ctx = MagicMock(spec=RuntimeContext)
    ctx.get_pipeline.return_value = pipeline_cfg
    ctx.get_detection_rules.return_value = []
    ctx.agent_pool = MagicMock()
    ctx.tool_pool = MagicMock()
    ctx.mcp_pool = MagicMock()
    return ctx


@pytest.mark.asyncio
async def test_single_agent_execute_called():
    """SINGLE_AGENT 流水线调用 SingleAgentNode.execute()。"""
    ctx = _make_context("SINGLE_AGENT")
    expected = AgentResult(
        answer="ok",
        tools_called=["weather"],
        session_id="sess-1",
        latency_ms=12,
        pipeline_type="SINGLE_AGENT",
    )

    with patch("src.agents.single_agent.SingleAgentNode.execute", new=AsyncMock(return_value=expected)), \
         patch("src.services.query_service.run_pre_detection", new=AsyncMock()), \
         patch("src.services.query_service.run_post_detection", new=AsyncMock()):
        result = await execute_query(ctx, "pl-001", "查天气", session_id="sess-1")

    assert result["answer"] == "ok"
    assert result["pipeline_type"] == "SINGLE_AGENT"


@pytest.mark.asyncio
async def test_multi_agent_execute_called():
    """MULTI_AGENT 流水线调用 MultiAgentNode.execute()。"""
    ctx = _make_context("MULTI_AGENT")
    expected = AgentResult(
        answer="多 Agent 回答",
        tools_called=[],
        session_id="sess-2",
        latency_ms=23,
        pipeline_type="MULTI_AGENT",
    )

    with patch("src.agents.multi_agent.MultiAgentNode.execute", new=AsyncMock(return_value=expected)), \
         patch("src.services.query_service.run_pre_detection", new=AsyncMock()), \
         patch("src.services.query_service.run_post_detection", new=AsyncMock()):
        result = await execute_query(ctx, "pl-001", "多 Agent 查询", session_id="sess-2")

    assert result["answer"] == "多 Agent 回答"
    assert result["pipeline_type"] == "MULTI_AGENT"


@pytest.mark.asyncio
async def test_pre_detection_blocks_query():
    """前置检测命中时抛出 PreCheckRejected，不执行 Agent。"""
    ctx = _make_context("SINGLE_AGENT")
    execute_mock = AsyncMock()

    with patch("src.agents.single_agent.SingleAgentNode.execute", new=execute_mock), \
         patch("src.services.query_service.run_pre_detection",
               new=AsyncMock(side_effect=PreCheckRejected("blocked"))), \
         patch("src.services.query_service.run_post_detection", new=AsyncMock()):
        with pytest.raises(PreCheckRejected, match="blocked"):
            await execute_query(ctx, "pl-001", "敏感查询")

    execute_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_pipeline_not_found_raises():
    """流水线不存在时抛出 ResourceNotFound。"""
    from src.core.exceptions import ResourceNotFound

    ctx = _make_context()
    ctx.get_pipeline.return_value = None

    with pytest.raises(ResourceNotFound):
        await execute_query(ctx, "nonexistent", "查询")
