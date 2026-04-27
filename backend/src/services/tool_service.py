from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ResourceConflict, ResourceNotFound
from src.models.tool import Tool, ToolProtocol
from src.services.config_cache import _serialize_model
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


class ToolService:
    async def list(
        self,
        db: AsyncSession,
        protocol: str | None = None,
        enabled: bool | None = None,
        keyword: str | None = None,
        mcp_server_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Tool], int]:
        q = select(Tool)
        if protocol:
            q = q.where(Tool.protocol == protocol)
        if enabled is not None:
            q = q.where(Tool.enabled == enabled)
        if keyword:
            q = q.where(Tool.name.contains(keyword) | Tool.display_name.contains(keyword))
        if mcp_server_id is not None:
            q = q.where(Tool.mcp_server_id == mcp_server_id)
        total_q = select(func.count()).select_from(q.subquery())
        total = (await db.execute(total_q)).scalar_one()
        q = q.offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(q)).scalars().all()
        return items, total

    async def get(self, db: AsyncSession, tool_id: int) -> Tool:
        obj = await db.get(Tool, tool_id)
        if not obj:
            raise ResourceNotFound(f"工具 {tool_id} 不存在")
        return obj

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> Tool:
        exists = (await db.execute(select(Tool).where(Tool.name == data["name"]))).scalar_one_or_none()
        if exists:
            raise ResourceConflict("工具名称已存在")
        obj = Tool(**data)
        db.add(obj)
        await db.flush()
        await event_bus.publish(_build_event("tool", obj.id, "create", _serialize_model(obj)))
        return obj

    async def update(self, db: AsyncSession, tool_id: int, data: dict[str, Any]) -> Tool:
        obj = await self.get(db, tool_id)
        for k, v in data.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.now(timezone.utc)
        return obj

    async def delete(self, db: AsyncSession, tool_id: int) -> None:
        obj = await self.get(db, tool_id)
        await db.delete(obj)
        await event_bus.publish(_build_event("tool", obj.id, "delete"))

    async def toggle(self, db: AsyncSession, tool_id: int, enabled: bool) -> Tool:
        obj = await self.get(db, tool_id)
        obj.enabled = enabled
        obj.updated_at = datetime.now(timezone.utc)
        await event_bus.publish(
            _build_event(
                "tool",
                obj.id,
                "enable" if enabled else "disable",
                _serialize_model(obj) if enabled else None,
            )
        )
        return obj
