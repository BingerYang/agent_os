from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.agent import Agent
from src.models.detection_rule import DetectionRule
from src.models.skill import Skill
from src.models.tool import Tool


def _serialize_model(obj: Any) -> dict[str, Any]:
    return jsonable_encoder({column.name: getattr(obj, column.name) for column in obj.__table__.columns})


def _serialize_skill(skill: Skill) -> dict[str, Any]:
    data = _serialize_model(skill)
    data["tool_ids"] = [tool.id for tool in skill.__dict__.get("tools", [])]
    return data


def _serialize_agent(agent: Agent) -> dict[str, Any]:
    data = _serialize_model(agent)
    data["tool_ids"] = [tool.id for tool in agent.__dict__.get("tools", [])]
    data["skill_ids"] = [skill.id for skill in agent.__dict__.get("skills", [])]
    return data


class ConfigCache:
    def __init__(self) -> None:
        self._tools: dict[int, dict[str, Any]] = {}
        self._skills: dict[int, dict[str, Any]] = {}
        self._agents: dict[int, dict[str, Any]] = {}
        self._detection_rules: dict[int, dict[str, Any]] = {}
        self._loaded = False

    async def load_snapshot(self, db: AsyncSession) -> None:
        """从数据库加载所有 enabled=True 的条目到内存"""
        tools = (
            await db.execute(
                select(Tool).where(Tool.enabled.is_(True)).order_by(Tool.id)
            )
        ).scalars().all()
        skills = (
            await db.execute(
                select(Skill)
                .where(Skill.enabled.is_(True))
                .options(selectinload(Skill.tools))
                .order_by(Skill.id)
            )
        ).scalars().all()
        agents = (
            await db.execute(
                select(Agent)
                .where(Agent.enabled.is_(True))
                .options(selectinload(Agent.tools), selectinload(Agent.skills))
                .order_by(Agent.id)
            )
        ).scalars().all()
        detection_rules = (
            await db.execute(
                select(DetectionRule).where(DetectionRule.enabled.is_(True)).order_by(DetectionRule.id)
            )
        ).scalars().all()

        self._tools = {tool.id: _serialize_model(tool) for tool in tools}
        self._skills = {skill.id: _serialize_skill(skill) for skill in skills}
        self._agents = {agent.id: _serialize_agent(agent) for agent in agents}
        self._detection_rules = {
            rule.id: _serialize_model(rule) for rule in detection_rules
        }
        self._loaded = True

    def apply_event(self, event: dict[str, Any]) -> None:
        """增量更新缓存：action=enable 时加入，action=disable 时移除"""
        entity_type = event.get("entity_type")
        entity_id = event.get("entity_id")
        action = event.get("action")

        if not isinstance(entity_id, int):
            return

        store = self._get_store(entity_type)
        if store is None:
            return

        if action in {"disable", "delete"}:
            store.pop(entity_id, None)
            return

        if action in {"enable", "create"}:
            payload = self._extract_payload(event)
            payload["id"] = entity_id
            store[entity_id] = payload

    def get_enabled_tools(self) -> list[dict[str, Any]]:
        return list(self._tools.values())

    def get_enabled_skills(self) -> list[dict[str, Any]]:
        return list(self._skills.values())

    def get_enabled_agents(self) -> list[dict[str, Any]]:
        return list(self._agents.values())

    def get_enabled_detection_rules(self) -> list[dict[str, Any]]:
        return list(self._detection_rules.values())

    def is_loaded(self) -> bool:
        return self._loaded

    def _get_store(self, entity_type: str | None) -> dict[int, dict[str, Any]] | None:
        if entity_type is None:
            return None
        stores = {
            "tool": self._tools,
            "skill": self._skills,
            "agent": self._agents,
            "detection_rule": self._detection_rules,
        }
        return stores.get(entity_type)

    def _extract_payload(self, event: dict[str, Any]) -> dict[str, Any]:
        payload = event.get("entity")
        if isinstance(payload, dict):
            return jsonable_encoder(payload)

        payload = event.get("data")
        if isinstance(payload, dict):
            return jsonable_encoder(payload)

        standard_keys = {"entity_type", "entity_id", "action", "timestamp"}
        extra_fields = {key: value for key, value in event.items() if key not in standard_keys}
        if extra_fields:
            return jsonable_encoder(extra_fields)

        return {}


config_cache = ConfigCache()
