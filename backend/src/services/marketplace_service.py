import json
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import JSON, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import BusinessValidationError, ResourceConflict, ResourceNotFound
from src.models.agent import Agent, AgentType
from src.models.skill import Skill
from src.models.tool import Tool
from src.services.config_cache import _serialize_agent, _serialize_model, _serialize_skill
from src.services.event_bus import event_bus

SUPPORTED_ITEM_TYPES = {"tool", "skill", "agent"}
MarketplaceItem = Tool | Skill | Agent


def _build_event(entity_type: str, entity_id: int, action: str, entity: dict | None = None) -> dict:
    event = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if entity is not None:
        event["entity"] = entity
    return event


class MarketplaceService:
    async def get_marketplace_items(
        self,
        db: AsyncSession,
        item_type: str | None = None,
        enabled: bool | None = None,
        keyword: str | None = None,
        tag: str | None = None,
    ) -> list[dict]:
        """UNION 查询 Tool / Skill / Agent，返回统一结构条目。"""
        normalized_item_type = self._normalize_item_type(item_type) if item_type else None

        tool_query = select(
            Tool.id.label("id"),
            Tool.name.label("name"),
            func.coalesce(Tool.description, "").label("description"),
            literal("tool").label("item_type"),
            Tool.enabled.label("enabled"),
            func.coalesce(Tool.tags, literal([], type_=JSON)).label("tags"),
            func.coalesce(Tool.version, "1.0.0").label("version"),
            func.coalesce(Tool.source_platform, "local").label("source_platform"),
            (
                func.coalesce(Tool.name, "")
                + literal(" ")
                + func.coalesce(Tool.display_name, "")
            ).label("search_text"),
        )

        skill_query = select(
            Skill.id.label("id"),
            Skill.name.label("name"),
            func.coalesce(Skill.description, "").label("description"),
            literal("skill").label("item_type"),
            Skill.enabled.label("enabled"),
            func.coalesce(Skill.tags, literal([], type_=JSON)).label("tags"),
            func.coalesce(Skill.version, "1.0.0").label("version"),
            literal("local").label("source_platform"),
            func.coalesce(Skill.name, "").label("search_text"),
        )

        agent_query = select(
            Agent.id.label("id"),
            Agent.name.label("name"),
            func.coalesce(Agent.description, "").label("description"),
            literal("agent").label("item_type"),
            Agent.enabled.label("enabled"),
            literal([], type_=JSON).label("tags"),
            literal("1.0.0").label("version"),
            func.coalesce(Agent.source_platform, "local").label("source_platform"),
            (
                func.coalesce(Agent.name, "")
                + literal(" ")
                + func.coalesce(Agent.source_platform, "")
            ).label("search_text"),
        )

        marketplace_query = union_all(tool_query, skill_query, agent_query).subquery()
        query = select(marketplace_query)

        if normalized_item_type:
            query = query.where(marketplace_query.c.item_type == normalized_item_type)
        if enabled is not None:
            query = query.where(marketplace_query.c.enabled == enabled)
        if keyword:
            query = query.where(
                marketplace_query.c.search_text.contains(keyword)
                | marketplace_query.c.description.contains(keyword)
            )

        rows = (await db.execute(query.order_by(marketplace_query.c.item_type, marketplace_query.c.id.desc()))).mappings().all()

        items = [
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"] or "",
                "item_type": row["item_type"],
                "enabled": bool(row["enabled"]),
                "tags": self._normalize_tags(row["tags"]),
                "version": row["version"] or "1.0.0",
                "source_platform": row["source_platform"] or "local",
            }
            for row in rows
        ]

        if tag:
            items = [item for item in items if tag in item["tags"]]

        return items

    async def install_item(self, db: AsyncSession, item_type: str, item_id: int) -> dict[str, Any]:
        normalized_item_type = self._normalize_item_type(item_type)
        obj = await self._get_item(db, item_type, item_id)
        obj.enabled = True
        obj.updated_at = datetime.now(UTC)
        await db.flush()
        await event_bus.publish(
            _build_event(
                normalized_item_type,
                obj.id,
                "enable",
                self._serialize_item(obj, normalized_item_type),
            )
        )
        return self._to_item_dict(obj, normalized_item_type)

    async def uninstall_item(self, db: AsyncSession, item_type: str, item_id: int) -> dict[str, Any]:
        normalized_item_type = self._normalize_item_type(item_type)
        obj = await self._get_item(db, item_type, item_id)
        obj.enabled = False
        obj.updated_at = datetime.now(UTC)
        await db.flush()
        await event_bus.publish(_build_event(normalized_item_type, obj.id, "disable"))
        return self._to_item_dict(obj, normalized_item_type)

    async def register_third_party_agent(
        self,
        db: AsyncSession,
        name: str,
        access_url: str,
        access_token: str,
        description: str = "",
    ) -> Agent:
        exists = (await db.execute(select(Agent).where(Agent.name == name))).scalar_one_or_none()
        if exists:
            raise ResourceConflict("智能体名称已存在")

        await self._ping_access_url(access_url)

        agent = Agent(
            name=name,
            description=description,
            agent_type=AgentType.SUB,
            source_platform="local",
            access_url=access_url,
            access_token=access_token,
            enabled=True,
        )
        db.add(agent)
        await db.flush()
        await event_bus.publish(
            _build_event(
                "agent",
                agent.id,
                "create",
                {
                    **_serialize_model(agent),
                    "tool_ids": [],
                    "skill_ids": [],
                },
            )
        )
        return agent

    async def _ping_access_url(self, access_url: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(access_url)
                response.raise_for_status()
        except Exception as exc:
            raise ValueError("访问地址不可达") from exc

    async def _get_item(self, db: AsyncSession, item_type: str, item_id: int) -> MarketplaceItem:
        normalized_item_type = self._normalize_item_type(item_type)

        if normalized_item_type == "tool":
            tool_obj = await db.get(Tool, item_id)
            if not tool_obj:
                raise ResourceNotFound(f"工具 {item_id} 不存在")
            return tool_obj

        if normalized_item_type == "skill":
            skill_obj = (
                await db.execute(
                    select(Skill)
                    .where(Skill.id == item_id)
                    .options(selectinload(Skill.tools))
                )
            ).scalar_one_or_none()
            if not skill_obj:
                raise ResourceNotFound(f"技能 {item_id} 不存在")
            return skill_obj

        agent_obj = (
            await db.execute(
                select(Agent)
                .where(Agent.id == item_id)
                .options(selectinload(Agent.tools), selectinload(Agent.skills))
            )
        ).scalar_one_or_none()
        if not agent_obj:
            raise ResourceNotFound(f"智能体 {item_id} 不存在")
        return agent_obj

    def _normalize_item_type(self, item_type: str) -> str:
        normalized_item_type = item_type.lower()
        if normalized_item_type not in SUPPORTED_ITEM_TYPES:
            raise BusinessValidationError("不支持的条目类型，仅支持工具、技能、智能体")
        return normalized_item_type

    def _normalize_tags(self, tags: object) -> list[Any]:
        if tags is None:
            return []
        if isinstance(tags, list):
            return tags
        if isinstance(tags, tuple):
            return list(tags)
        if isinstance(tags, str):
            try:
                parsed = json.loads(tags)
            except json.JSONDecodeError:
                return []
            return parsed if isinstance(parsed, list) else []
        return []

    def _to_item_dict(self, obj: MarketplaceItem, item_type: str | None = None) -> dict[str, Any]:
        data = {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
        if item_type is not None:
            data["item_type"] = item_type
        return data

    def _serialize_item(self, obj: MarketplaceItem, item_type: str) -> dict[str, Any]:
        if item_type == "tool":
            return _serialize_model(obj)
        if item_type == "skill":
            if not isinstance(obj, Skill):
                raise TypeError("expected Skill for skill serialization")
            return _serialize_skill(obj)
        if not isinstance(obj, Agent):
            raise TypeError("expected Agent for agent serialization")
        return _serialize_agent(obj)
