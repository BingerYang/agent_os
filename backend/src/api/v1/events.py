from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from src.core.config import get_settings
from src.core.database import get_db
from src.core.schemas import ApiResponse
from src.models.agent import Agent
from src.models.detection_rule import DetectionRule
from src.models.skill import Skill
from src.models.tool import Tool
from src.services.event_bus import event_bus

router = APIRouter()


def _serialize_model(obj: Any) -> dict:
    return jsonable_encoder({column.name: getattr(obj, column.name) for column in obj.__table__.columns})


def _serialize_skill(skill: Skill) -> dict:
    data = _serialize_model(skill)
    data["tool_ids"] = [tool.id for tool in skill.tools]
    return data


def _serialize_agent(agent: Agent) -> dict:
    data = _serialize_model(agent)
    data["tool_ids"] = [tool.id for tool in agent.tools]
    data["skill_ids"] = [skill.id for skill in agent.skills]
    return data


@router.get("/events/stream")
async def event_stream(request: Request) -> EventSourceResponse:
    settings = get_settings()
    test_mode = settings.database_url == "sqlite+aiosqlite:///:memory:"

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        subscriber = event_bus.subscribe()
        next_event_task: asyncio.Task | None = None
        try:
            yield {
                "data": json.dumps(
                    {
                        "event_type": "ping",
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                    ensure_ascii=False,
                )
            }
            if test_mode:
                return

            next_event_task = asyncio.create_task(subscriber.__anext__())
            while True:
                if await request.is_disconnected():
                    break

                done, _ = await asyncio.wait({next_event_task}, timeout=0.5)
                if not done:
                    continue

                try:
                    event = await next_event_task
                except StopAsyncIteration:
                    break

                yield {"data": json.dumps(jsonable_encoder(event), ensure_ascii=False)}
                next_event_task = asyncio.create_task(subscriber.__anext__())
        except (asyncio.CancelledError, GeneratorExit):
            raise
        finally:
            if next_event_task is not None and not next_event_task.done():
                next_event_task.cancel()
                try:
                    await next_event_task
                except (asyncio.CancelledError, StopAsyncIteration):
                    pass
            await subscriber.aclose()

    return EventSourceResponse(event_generator())


@router.get("/config/snapshot")
async def config_snapshot(db: AsyncSession = Depends(get_db)) -> ApiResponse[Any]:
    tools = (
        await db.execute(select(Tool).where(Tool.enabled.is_(True)).order_by(Tool.id))
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

    return ApiResponse.ok(
        {
            "tools": [_serialize_model(tool) for tool in tools],
            "skills": [_serialize_skill(skill) for skill in skills],
            "agents": [_serialize_agent(agent) for agent in agents],
            "detection_rules": [_serialize_model(rule) for rule in detection_rules],
        }
    )
