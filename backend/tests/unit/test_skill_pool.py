"""T039: 单元测试 - SkillPool 覆盖率补充。"""
from __future__ import annotations

import pytest

from src.agents.pool.skill_pool import SkillPool, SkillPoolEntry


def _make_snapshot_skills() -> list[dict]:
    return [
        {"id": 1, "name": "search", "description": "搜索工具", "tool_ids": [10, 11]},
        {"id": 2, "name": "calc", "description": "计算", "tool_ids": []},
    ]


def test_build_from_snapshot_populates_pool():
    """build_from_snapshot 正确构建条目。"""
    pool = SkillPool()
    pool.build_from_snapshot(_make_snapshot_skills())
    assert pool.size() == 2


def test_get_returns_entry_by_id():
    """get() 按 ID 返回正确条目。"""
    pool = SkillPool()
    pool.build_from_snapshot(_make_snapshot_skills())
    entry = pool.get(1)
    assert entry is not None
    assert entry.skill_id == 1
    assert entry.name == "search"
    assert entry.tool_ids == [10, 11]


def test_get_returns_none_for_missing_id():
    """get() 对不存在 ID 返回 None。"""
    pool = SkillPool()
    assert pool.get(999) is None


def test_invalidate_removes_entry():
    """invalidate() 移除指定条目。"""
    pool = SkillPool()
    pool.build_from_snapshot(_make_snapshot_skills())
    pool.invalidate(1)
    assert pool.get(1) is None
    assert pool.size() == 1


def test_invalidate_noop_for_missing_id():
    """invalidate() 对不存在 ID 不报错。"""
    pool = SkillPool()
    pool.invalidate(999)  # 不抛出


def test_build_from_snapshot_empty_list():
    """空列表构建后 size 为 0。"""
    pool = SkillPool()
    pool.build_from_snapshot([])
    assert pool.size() == 0


def test_build_from_snapshot_overwrites_existing():
    """相同 ID 的条目被覆盖（热更新语义）。"""
    pool = SkillPool()
    pool.build_from_snapshot([{"id": 1, "name": "old", "description": "", "tool_ids": []}])
    pool.build_from_snapshot([{"id": 1, "name": "new", "description": "", "tool_ids": []}])
    assert pool.get(1).name == "new"  # type: ignore[union-attr]
    assert pool.size() == 1
