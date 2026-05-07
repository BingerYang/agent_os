"""T039: 单元测试 - runtime/loader.py 覆盖率提升。"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.runtime.loader import _reload_agent, start_redis_subscriber, stop_redis_subscriber


# ---------- stop/start_redis_subscriber ----------

@pytest.mark.asyncio
async def test_start_redis_subscriber_returns_task():
    """start_redis_subscriber 返回 asyncio.Task。"""
    from src.agents.pool.agent_pool import AgentPool
    from src.agents.pool.mcp_pool import MCPConnectionPool
    from src.agents.pool.skill_pool import SkillPool
    from src.agents.pool.tool_pool import ToolPool
    from src.runtime.context import RuntimeContext

    ctx = RuntimeContext(
        agent_pool=AgentPool(),
        tool_pool=ToolPool(),
        skill_pool=SkillPool(),
        mcp_pool=MCPConnectionPool(),
        pipeline_cache={},
        detection_cache={},
    )

    with patch("src.runtime.loader._redis_subscriber_loop", new=AsyncMock()):
        task = start_redis_subscriber(ctx, "agent:publish")
        assert isinstance(task, asyncio.Task)
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


def test_stop_redis_subscriber_cancels_running_task():
    """stop_redis_subscriber 取消运行中的 Task。"""
    mock_task = MagicMock(spec=asyncio.Task)
    mock_task.done.return_value = False

    stop_redis_subscriber(mock_task)
    mock_task.cancel.assert_called_once()


def test_stop_redis_subscriber_noop_on_done_task():
    """stop_redis_subscriber 对已完成的 Task 不调用 cancel。"""
    mock_task = MagicMock(spec=asyncio.Task)
    mock_task.done.return_value = True

    stop_redis_subscriber(mock_task)
    mock_task.cancel.assert_not_called()


def test_stop_redis_subscriber_noop_on_none():
    """stop_redis_subscriber 传 None 不报错。"""
    stop_redis_subscriber(None)  # type: ignore[arg-type]


# ---------- _reload_agent ----------

@pytest.mark.asyncio
async def test_reload_agent_publish_not_found_logs_warning():
    """publish 记录不存在时记录 warning 并返回（不抛出）。"""
    from src.agents.pool.agent_pool import AgentPool
    from src.agents.pool.mcp_pool import MCPConnectionPool
    from src.agents.pool.skill_pool import SkillPool
    from src.agents.pool.tool_pool import ToolPool
    from src.runtime.context import RuntimeContext

    ctx = RuntimeContext(
        agent_pool=AgentPool(),
        tool_pool=ToolPool(),
        skill_pool=SkillPool(),
        mcp_pool=MCPConnectionPool(),
        pipeline_cache={},
        detection_cache={},
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    await _reload_agent(db=mock_db, agent_id=99, publish_id=999, context=ctx)


@pytest.mark.asyncio
async def test_reload_agent_success_upserts_pool():
    """publish 存在时构建 entry 并 upsert 到 agent_pool。"""
    from src.agents.pool.agent_pool import AgentPool, AgentPoolEntry
    from src.agents.pool.mcp_pool import MCPConnectionPool
    from src.agents.pool.skill_pool import SkillPool
    from src.agents.pool.tool_pool import ToolPool
    from src.runtime.context import RuntimeContext

    ctx = RuntimeContext(
        agent_pool=AgentPool(),
        tool_pool=ToolPool(),
        skill_pool=SkillPool(),
        mcp_pool=MCPConnectionPool(),
        pipeline_cache={},
        detection_cache={},
    )

    mock_pub = MagicMock()
    mock_pub.agent_id = 1
    mock_pub.version = 2
    mock_pub.config_snapshot = {"agent_id": 1, "agent_type": "SINGLE", "tools": [], "skills": []}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_pub)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    now = datetime.now(timezone.utc)
    fake_entry = AgentPoolEntry(
        agent_id=1,
        version=2,
        agent_type="SINGLE",
        compiled_graph=MagicMock(),
        loaded_at=now,
        last_accessed_at=now,
    )

    with patch("src.agents.pool.agent_pool.AgentPool.build_entry", new=AsyncMock(return_value=fake_entry)), \
            patch.object(ctx.tool_pool, "build_from_snapshot", new=AsyncMock()), \
            patch.object(ctx.skill_pool, "build_from_snapshot", new=MagicMock()):
        await _reload_agent(db=mock_db, agent_id=1, publish_id=5, context=ctx)

    assert ctx.agent_pool.get(1) is not None


@pytest.mark.asyncio
async def test_reload_agent_db_error_logged_not_raised():
    """DB 查询抛出异常时记录 error，不向上传播。"""
    from src.agents.pool.agent_pool import AgentPool
    from src.agents.pool.mcp_pool import MCPConnectionPool
    from src.agents.pool.skill_pool import SkillPool
    from src.agents.pool.tool_pool import ToolPool
    from src.runtime.context import RuntimeContext

    ctx = RuntimeContext(
        agent_pool=AgentPool(),
        tool_pool=ToolPool(),
        skill_pool=SkillPool(),
        mcp_pool=MCPConnectionPool(),
        pipeline_cache={},
        detection_cache={},
    )

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=RuntimeError("db exploded"))

    await _reload_agent(db=mock_db, agent_id=1, publish_id=5, context=ctx)


# ---------- load_from_db ----------

@pytest.mark.asyncio
async def test_load_from_db_returns_runtime_context():
    """load_from_db 返回正确的 RuntimeContext（使用 mock DB）。"""
    from src.runtime.context import RuntimeContext
    from src.runtime.loader import load_from_db

    mock_pipeline = MagicMock()
    mock_pipeline.uid = "pl-001"
    mock_pipeline.id = 1
    mock_pipeline.primary_agent_id = 1
    mock_pipeline.pipeline_type = MagicMock(value="SINGLE_AGENT")
    mock_pipeline.detection_rules = []
    mock_pipeline.route_confidence_threshold = 0.7
    mock_pipeline.timeout_seconds = 30
    mock_pipeline.enabled = True

    def make_scalars(items):
        m = MagicMock()
        m.scalars.return_value.all.return_value = items
        return m

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        make_scalars([mock_pipeline]),
        make_scalars([]),
        make_scalars([]),
    ])

    ctx = await load_from_db(mock_db)

    assert isinstance(ctx, RuntimeContext)
    assert "pl-001" in ctx.pipeline_cache


@pytest.mark.asyncio
async def test_load_from_db_db_error_propagates():
    """load_from_db DB 异常向上抛出（Fail Fast）。"""
    from src.runtime.loader import load_from_db

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=RuntimeError("db dead"))

    with pytest.raises(RuntimeError, match="db dead"):
        await load_from_db(mock_db)


@pytest.mark.asyncio
async def test_load_from_db_skips_pipeline_without_uid():
    """uid 为 None 的 Pipeline 跳过，不进 cache。"""
    from src.runtime.loader import load_from_db

    mock_pipeline = MagicMock()
    mock_pipeline.uid = None
    mock_pipeline.primary_agent_id = 1

    def make_scalars(items):
        m = MagicMock()
        m.scalars.return_value.all.return_value = items
        return m

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        make_scalars([mock_pipeline]),
        make_scalars([]),
        make_scalars([]),
    ])

    ctx = await load_from_db(mock_db)
    assert len(ctx.pipeline_cache) == 0


@pytest.mark.asyncio
async def test_load_from_db_with_detection_rules():
    """load_from_db 正确加载检测规则到 detection_cache。"""
    from src.runtime.loader import load_from_db

    mock_rule = MagicMock()
    mock_rule.id = 42

    def make_scalars(items):
        m = MagicMock()
        m.scalars.return_value.all.return_value = items
        return m

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        make_scalars([]),  # pipelines
        make_scalars([mock_rule]),  # detection rules
        make_scalars([]),  # agent publishes
    ])

    ctx = await load_from_db(mock_db)
    assert 42 in ctx.detection_cache


@pytest.mark.asyncio
async def test_load_from_db_detection_rules_error_propagates():
    """detection rules 查询失败时向上抛出。"""
    from src.runtime.loader import load_from_db

    def make_scalars(items):
        m = MagicMock()
        m.scalars.return_value.all.return_value = items
        return m

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        make_scalars([]),  # pipelines OK
        RuntimeError("rules db fail"),  # detection rules fail
    ])

    with pytest.raises(RuntimeError, match="rules db fail"):
        await load_from_db(mock_db)


@pytest.mark.asyncio
async def test_load_from_db_agent_publishes_error_propagates():
    """agent publishes 查询失败时向上抛出。"""
    from src.runtime.loader import load_from_db

    def make_scalars(items):
        m = MagicMock()
        m.scalars.return_value.all.return_value = items
        return m

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        make_scalars([]),  # pipelines OK
        make_scalars([]),  # detection rules OK
        RuntimeError("publish db fail"),  # agent publishes fail
    ])

    with pytest.raises(RuntimeError, match="publish db fail"):
        await load_from_db(mock_db)


@pytest.mark.asyncio
async def test_load_from_db_with_agent_publish_success():
    """成功加载 agent publish 时 agent_pool 中有对应条目。"""
    from datetime import datetime, timezone

    from src.agents.pool.agent_pool import AgentPoolEntry
    from src.runtime.loader import load_from_db

    mock_pub = MagicMock()
    mock_pub.agent_id = 1
    mock_pub.version = 1
    mock_pub.config_snapshot = {"agent_id": 1, "agent_type": "SINGLE", "tools": [], "skills": []}

    def make_scalars(items):
        m = MagicMock()
        m.scalars.return_value.all.return_value = items
        return m

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        make_scalars([]),  # pipelines
        make_scalars([]),  # detection rules
        make_scalars([mock_pub]),  # agent publishes
    ])

    now = datetime.now(timezone.utc)
    fake_entry = AgentPoolEntry(
        agent_id=1, version=1, agent_type="SINGLE",
        compiled_graph=MagicMock(), loaded_at=now, last_accessed_at=now,
    )

    with patch("src.agents.pool.agent_pool.AgentPool.build_entry", new=AsyncMock(return_value=fake_entry)), \
            patch("src.agents.pool.tool_pool.ToolPool.build_from_snapshot", new=AsyncMock()), \
            patch("src.agents.pool.skill_pool.SkillPool.build_from_snapshot", new=MagicMock()):
        ctx = await load_from_db(mock_db)

    assert ctx.agent_pool.get(1) is not None


@pytest.mark.asyncio
async def test_load_from_db_agent_publish_build_error_skipped():
    """agent publish 构建出错时跳过（warning），不影响其他加载。"""
    from src.runtime.loader import load_from_db

    mock_pub = MagicMock()
    mock_pub.agent_id = 99
    mock_pub.version = 1
    mock_pub.config_snapshot = {}

    def make_scalars(items):
        m = MagicMock()
        m.scalars.return_value.all.return_value = items
        return m

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[
        make_scalars([]),
        make_scalars([]),
        make_scalars([mock_pub]),
    ])

    with patch("src.agents.pool.agent_pool.AgentPool.build_entry",
               new=AsyncMock(side_effect=RuntimeError("build fail"))), \
            patch("src.agents.pool.tool_pool.ToolPool.build_from_snapshot", new=AsyncMock()), \
            patch("src.agents.pool.skill_pool.SkillPool.build_from_snapshot", new=MagicMock()):
        ctx = await load_from_db(mock_db)  # 不抛出

    assert ctx.agent_pool.get(99) is None
