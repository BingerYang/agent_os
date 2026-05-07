"""技能池：从 AgentPublish.config_snapshot 构建并缓存 Skill 对象。"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class SkillPoolEntry:
    """技能池中的单个技能条目。

    Attributes:
        skill_id: 技能 ID。
        name: 技能名称。
        description: 技能描述。
        tool_ids: 该技能关联的工具 ID 列表。
        loaded_at: 条目加载时间。
    """

    skill_id: int
    name: str
    description: str
    tool_ids: list[int] = field(default_factory=list)
    loaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SkillPool:
    """运行时技能池，从 config_snapshot 构建，零数据库读取。

    Usage:
        pool = SkillPool()
        pool.build_from_snapshot(agent_snapshot["skills"])
        entry = pool.get(skill_id=1)
    """

    def __init__(self) -> None:
        self._pool: dict[int, SkillPoolEntry] = {}

    def build_from_snapshot(self, snapshot_skills: list[dict]) -> None:
        """从 config_snapshot 的 skills 字段批量构建技能条目。

        Args:
            snapshot_skills: config_snapshot["skills"] 列表，每项包含
                id、name、description、tool_ids 字段。
        """
        for skill in snapshot_skills:
            entry = SkillPoolEntry(
                skill_id=int(skill["id"]),
                name=str(skill.get("name", "")),
                description=str(skill.get("description", "")),
                tool_ids=[int(tid) for tid in skill.get("tool_ids", [])],
            )
            self._pool[entry.skill_id] = entry
        logger.debug("skill_pool.built count=%d", len(self._pool))

    def get(self, skill_id: int) -> SkillPoolEntry | None:
        """按 ID 查询技能条目。

        Args:
            skill_id: 技能 ID。

        Returns:
            对应的 SkillPoolEntry，不存在时返回 None。
        """
        return self._pool.get(skill_id)

    def invalidate(self, skill_id: int) -> None:
        """从池中移除指定技能（热更新时使用）。

        Args:
            skill_id: 要移除的技能 ID。
        """
        self._pool.pop(skill_id, None)

    def size(self) -> int:
        """返回当前池中的技能数量。"""
        return len(self._pool)
