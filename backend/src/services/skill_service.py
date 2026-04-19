from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ResourceConflict, ResourceNotFound
from src.models.skill import Skill
from src.models.tool import Tool
from src.services.config_cache import _serialize_skill
from src.services.event_bus import event_bus


def _build_event(entity_type: str, entity_id: int, action: str, entity: dict | None = None) -> dict:
    event = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if entity is not None:
        event["entity"] = entity
    return event


class SkillService:
    async def list(
        self,
        db: AsyncSession,
        enabled: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Skill], int]:
        q = select(Skill)
        if enabled is not None:
            q = q.where(Skill.enabled == enabled)
        if keyword:
            q = q.where(Skill.name.contains(keyword))
        total_q = select(func.count()).select_from(q.subquery())
        total = (await db.execute(total_q)).scalar_one()
        q = q.offset((page - 1) * page_size).limit(page_size).options(selectinload(Skill.tools))
        items = (await db.execute(q)).scalars().all()
        return items, total

    async def get(self, db: AsyncSession, skill_id: int) -> Skill:
        q = select(Skill).where(Skill.id == skill_id).options(selectinload(Skill.tools))
        obj = (await db.execute(q)).scalar_one_or_none()
        if not obj:
            raise ResourceNotFound(f"技能 {skill_id} 不存在")
        return obj

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> Skill:
        tool_ids: list[int] = data.pop("tool_ids", [])
        exists = (await db.execute(select(Skill).where(Skill.name == data["name"]))).scalar_one_or_none()
        if exists:
            raise ResourceConflict("技能名称已存在")
        obj = Skill(**data)
        if tool_ids:
            tool_objs = (await db.execute(select(Tool).where(Tool.id.in_(tool_ids)))).scalars().all()
            obj.tools = list(tool_objs)
        db.add(obj)
        await db.flush()
        await event_bus.publish(_build_event("skill", obj.id, "create", _serialize_skill(obj)))
        return obj

    async def update(self, db: AsyncSession, skill_id: int, data: dict[str, Any]) -> Skill:
        obj = await self.get(db, skill_id)
        tool_ids: list[int] | None = data.pop("tool_ids", None)
        for k, v in data.items():
            setattr(obj, k, v)
        if tool_ids is not None:
            tools = (await db.execute(select(Tool).where(Tool.id.in_(tool_ids)))).scalars().all()
            obj.tools = list(tools)
        obj.updated_at = datetime.now(timezone.utc)
        return obj

    async def delete(self, db: AsyncSession, skill_id: int) -> None:
        obj = await self.get(db, skill_id)
        await db.delete(obj)
        await event_bus.publish(_build_event("skill", obj.id, "delete"))

    async def toggle(self, db: AsyncSession, skill_id: int, enabled: bool) -> Skill:
        obj = await self.get(db, skill_id)
        obj.enabled = enabled
        obj.updated_at = datetime.now(timezone.utc)
        await event_bus.publish(
            _build_event(
                "skill",
                obj.id,
                "enable" if enabled else "disable",
                _serialize_skill(obj) if enabled else None,
            )
        )
        return obj
