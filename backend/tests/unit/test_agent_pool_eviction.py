"""T037: 单元测试 - AgentPool 淘汰策略高级验证。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.agents.pool.agent_pool import AgentPool, AgentPoolEntry


def _make_entry(agent_id: int, age_h: float = 1.0, idle_h: float = 1.0) -> AgentPoolEntry:
    """创建指定 age/idle 时长的 AgentPoolEntry。"""
    now = datetime.now(timezone.utc)
    return AgentPoolEntry(
        agent_id=agent_id,
        version=1,
        agent_type="SINGLE",
        compiled_graph=MagicMock(),
        loaded_at=now - timedelta(hours=age_h),
        last_accessed_at=now - timedelta(hours=idle_h),
    )


def test_eviction_score_formula():
    """淘汰评分公式：score = 0.3×age_h + 0.7×idle_h。"""
    pool = AgentPool()
    entry = _make_entry(agent_id=1, age_h=10.0, idle_h=20.0)
    score = pool._eviction_score(entry)
    # 0.3*10 + 0.7*20 = 3.0 + 14.0 = 17.0
    assert abs(score - 17.0) < 0.5


def test_evict_one_with_single_entry():
    """池中只有一个条目时 evict_one() 正常执行不报错。"""
    pool = AgentPool()
    pool.upsert(_make_entry(agent_id=5))
    evicted = pool.evict_one()
    assert evicted == 5
    assert pool.size() == 0


def test_upsert_does_not_evict_below_capacity():
    """池未满时 upsert 不触发淘汰。"""
    pool = AgentPool(max_size=5)
    for i in range(3):
        pool.upsert(_make_entry(agent_id=i + 1))
    assert pool.size() == 3


def test_upsert_update_does_not_grow_pool():
    """相同 agent_id 的 upsert 是更新操作，不增加池大小。"""
    pool = AgentPool(max_size=2)
    pool.upsert(_make_entry(agent_id=1, age_h=5.0))
    pool.upsert(_make_entry(agent_id=1, age_h=1.0))
    assert pool.size() == 1


def test_eviction_selects_highest_scoring_entry():
    """池满时淘汰评分最高（最老且最久未访问）的条目。"""
    pool = AgentPool(max_size=3)
    pool.upsert(_make_entry(agent_id=1, age_h=1.0, idle_h=1.0))    # score ~1.0
    pool.upsert(_make_entry(agent_id=2, age_h=20.0, idle_h=30.0))  # score ~27.0 → 被淘汰
    pool.upsert(_make_entry(agent_id=3, age_h=2.0, idle_h=2.0))    # score ~2.0
    pool.upsert(_make_entry(agent_id=4, age_h=0.5, idle_h=0.5))    # 触发淘汰

    assert pool.get(2) is None
    assert pool.size() == 3


def test_get_after_eviction_returns_none():
    """被淘汰的条目 get() 返回 None。"""
    pool = AgentPool(max_size=1)
    pool.upsert(_make_entry(agent_id=1, age_h=5.0, idle_h=5.0))
    pool.upsert(_make_entry(agent_id=2, age_h=0.1, idle_h=0.1))  # 触发淘汰 agent_id=1

    assert pool.get(1) is None
    assert pool.get(2) is not None
