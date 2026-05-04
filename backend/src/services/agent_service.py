from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ResourceConflict, ResourceNotFound
from src.models.agent import Agent
from src.models.tool import Tool
from src.models.skill import Skill
from src.services.config_cache import _serialize_agent
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


class AgentService:
    async def list(
        self,
        db: AsyncSession,
        agent_type: str | None = None,
        enabled: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Agent], int]:
        q = select(Agent)
        if agent_type:
            q = q.where(Agent.agent_type == agent_type)
        if enabled is not None:
            q = q.where(Agent.enabled == enabled)
        if keyword:
            q = q.where(Agent.name.contains(keyword))
        total_q = select(func.count()).select_from(q.subquery())
        total = (await db.execute(total_q)).scalar_one()
        q = q.offset((page - 1) * page_size).limit(page_size).options(
            selectinload(Agent.tools),
            selectinload(Agent.skills),
        )
        items = (await db.execute(q)).scalars().all()
        return items, total

    async def get(self, db: AsyncSession, agent_id: int) -> Agent:
        q = select(Agent).where(Agent.id == agent_id).options(
            selectinload(Agent.tools),
            selectinload(Agent.skills),
        )
        obj = (await db.execute(q)).scalar_one_or_none()
        if not obj:
            raise ResourceNotFound(f"Agent {agent_id} 不存在")
        return obj

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> Agent:
        tool_ids: list[int] = data.pop("tool_ids", [])
        skill_ids: list[int] = data.pop("skill_ids", [])
        exists = (await db.execute(select(Agent).where(Agent.name == data["name"]))).scalar_one_or_none()
        if exists:
            raise ResourceConflict("Agent 名称已存在")
        obj = Agent(**data)
        if tool_ids:
            tools_objs = (await db.execute(select(Tool).where(Tool.id.in_(tool_ids)))).scalars().all()
            obj.tools = list(tools_objs)
        if skill_ids:
            skill_objs = (await db.execute(select(Skill).where(Skill.id.in_(skill_ids)))).scalars().all()
            obj.skills = list(skill_objs)
        db.add(obj)
        await db.flush()
        await event_bus.publish(_build_event("agent", obj.id, "create", _serialize_agent(obj)))
        return obj

    async def update(self, db: AsyncSession, agent_id: int, data: dict[str, Any]) -> Agent:
        obj = await self.get(db, agent_id)
        tool_ids: list[int] | None = data.pop("tool_ids", None)
        skill_ids: list[int] | None = data.pop("skill_ids", None)
        for k, v in data.items():
            setattr(obj, k, v)
        if tool_ids is not None:
            tools = (await db.execute(select(Tool).where(Tool.id.in_(tool_ids)))).scalars().all()
            obj.tools = list(tools)
        if skill_ids is not None:
            skills = (await db.execute(select(Skill).where(Skill.id.in_(skill_ids)))).scalars().all()
            obj.skills = list(skills)
        obj.updated_at = datetime.now(timezone.utc)
        return obj

    async def publish(self, db: AsyncSession, agent_id: int, status: str) -> Agent:
        obj = await self.get(db, agent_id)
        obj.status = status
        obj.updated_at = datetime.now(timezone.utc)
        return obj

    async def delete(self, db: AsyncSession, agent_id: int) -> None:
        obj = await self.get(db, agent_id)
        await db.delete(obj)
        await event_bus.publish(_build_event("agent", obj.id, "delete"))

    async def toggle(self, db: AsyncSession, agent_id: int, enabled: bool) -> Agent:
        obj = await self.get(db, agent_id)
        obj.enabled = enabled
        obj.updated_at = datetime.now(timezone.utc)
        await event_bus.publish(
            _build_event(
                "agent",
                obj.id,
                "enable" if enabled else "disable",
                _serialize_agent(obj) if enabled else None,
            )
        )
        return obj
