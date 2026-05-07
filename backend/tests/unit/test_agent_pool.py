"""T021: TDD 单元测试 - AgentPool。"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.pool.agent_pool import AgentPool, AgentPoolEntry


def _make_entry(agent_id: int, age_h: float = 1.0, idle_h: float = 1.0) -> AgentPoolEntry:
    """创建测试用 AgentPoolEntry，可指定 age 和 idle 时长（小时）。"""
    now = datetime.now(timezone.utc)
    return AgentPoolEntry(
        agent_id=agent_id,
        version=1,
        agent_type="SINGLE",
        compiled_graph=MagicMock(),
        loaded_at=now - timedelta(hours=age_h),
        last_accessed_at=now - timedelta(hours=idle_h),
    )


def test_get_updates_last_accessed_at():
    """get() 更新 last_accessed_at 和 access_count。"""
    pool = AgentPool()
    entry = _make_entry(agent_id=1, idle_h=5.0)
    before = entry.last_accessed_at
    pool.upsert(entry)

    got = pool.get(1)
    assert got is not None
    assert got.last_accessed_at > before
    assert got.access_count == 1


def test_evict_one_removes_highest_score():
    """evict_one() 淘汰评分（0.3×age + 0.7×idle）最高的条目。"""
    pool = AgentPool()
    # entry_2: 老且长时间未访问 → 高分 → 应被淘汰
    pool.upsert(_make_entry(agent_id=1, age_h=1.0, idle_h=1.0))   # score ≈ 1.0
    pool.upsert(_make_entry(agent_id=2, age_h=10.0, idle_h=20.0)) # score ≈ 17.0 → 淘汰
    pool.upsert(_make_entry(agent_id=3, age_h=2.0, idle_h=2.0))   # score ≈ 2.0

    evicted_id = pool.evict_one()
    assert evicted_id == 2
    assert pool.size() == 2
    assert pool.get(2) is None


def test_upsert_respects_max_size():
    """池满时 upsert 自动触发淘汰，保持容量不超过 max_size。"""
    pool = AgentPool(max_size=2)
    pool.upsert(_make_entry(agent_id=1, age_h=5.0, idle_h=5.0))
    pool.upsert(_make_entry(agent_id=2, age_h=1.0, idle_h=1.0))
    pool.upsert(_make_entry(agent_id=3, age_h=0.1, idle_h=0.1))  # 触发淘汰

    assert pool.size() == 2
    # agent_id=1 是最老且最长时间未访问的，应被淘汰
    assert pool.get(1) is None


@pytest.mark.asyncio
async def test_on_eviction_hook_called():
    """evict_one() 调用 on_eviction hook（V1 为空实现，不抛出异常）。"""
    pool = AgentPool()
    pool.upsert(_make_entry(agent_id=1, age_h=2.0, idle_h=2.0))
    pool.upsert(_make_entry(agent_id=2, age_h=1.0, idle_h=1.0))

    # on_eviction 为空实现，不应抛出
    pool.evict_one()
    # 给 asyncio.create_task 一个机会执行
    await asyncio.sleep(0)
