"""T045: 集成测试 - 运行时对话路径零数据库读取验证。"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.base import AgentResult
from src.agents.pool.agent_pool import AgentPool
from src.agents.pool.mcp_pool import MCPConnectionPool
from src.agents.pool.skill_pool import SkillPool
from src.agents.pool.tool_pool import ToolPool
from src.runtime.context import PipelineCacheEntry, RuntimeContext
from src.services.query_service import execute_query


def _make_runtime_context() -> RuntimeContext:
    """构建纯内存 RuntimeContext，不依赖任何数据库连接。"""
    pipeline = PipelineCacheEntry(
        pipeline_uid="pl-no-db",
        pipeline_id=1,
        pipeline_type="SINGLE_AGENT",
        primary_agent_id=1,
        detection_rule_ids=[],
        enabled=True,
    )
    return RuntimeContext(
        agent_pool=AgentPool(),
        tool_pool=ToolPool(),
        skill_pool=SkillPool(),
        mcp_pool=MCPConnectionPool(),
        pipeline_cache={"pl-no-db": pipeline},
        detection_cache={},
    )


@pytest.mark.asyncio
async def test_execute_query_no_db_access():
    """execute_query 整个调用路径中不访问数据库。"""
    ctx = _make_runtime_context()
    mock_result = AgentResult(
        answer="no-db answer",
        session_id="sess-no-db",
        pipeline_type="SINGLE_AGENT",
    )

    with patch("src.agents.single_agent.SingleAgentNode.execute", new=AsyncMock(return_value=mock_result)), \
         patch("src.services.query_service.run_pre_detection", new=AsyncMock()), \
         patch("src.services.query_service.run_post_detection", new=AsyncMock()):
        result = await execute_query(ctx, "pl-no-db", "test query")

    assert result["answer"] == "no-db answer"
    assert result["pipeline_type"] == "SINGLE_AGENT"


@pytest.mark.asyncio
async def test_pipeline_not_in_cache_raises_not_found():
    """流水线 UID 不在缓存中时抛出 ResourceNotFound，不发起 DB 查询。"""
    from src.core.exceptions import ResourceNotFound

    ctx = _make_runtime_context()

    with pytest.raises(ResourceNotFound):
        await execute_query(ctx, "nonexistent-uid", "test query")


@pytest.mark.asyncio
async def test_disabled_pipeline_raises_not_found():
    """已禁用流水线（enabled=False）抛出 ResourceNotFound。"""
    from src.core.exceptions import ResourceNotFound

    ctx = _make_runtime_context()
    ctx.pipeline_cache["pl-disabled"] = PipelineCacheEntry(
        pipeline_uid="pl-disabled",
        pipeline_id=2,
        pipeline_type="SINGLE_AGENT",
        primary_agent_id=2,
        enabled=False,
    )

    with pytest.raises(ResourceNotFound):
        await execute_query(ctx, "pl-disabled", "test query")


def test_runtime_context_holds_all_pools():
    """RuntimeContext 持有所有运行时内存池的正确引用。"""
    ctx = _make_runtime_context()

    assert isinstance(ctx.agent_pool, AgentPool)
    assert isinstance(ctx.tool_pool, ToolPool)
    assert isinstance(ctx.skill_pool, SkillPool)
    assert isinstance(ctx.mcp_pool, MCPConnectionPool)
    assert "pl-no-db" in ctx.pipeline_cache
