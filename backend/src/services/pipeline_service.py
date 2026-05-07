from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ResourceNotFound
from src.models.agent import Agent
from src.models.detection_rule import DetectionRule
from src.models.pipeline import Pipeline


class PipelineService:
    async def list(
        self,
        db: AsyncSession,
        pipeline_type: str | None = None,
        enabled: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Pipeline], int]:
        q = select(Pipeline)
        if pipeline_type:
            q = q.where(Pipeline.pipeline_type == pipeline_type)
        if enabled is not None:
            q = q.where(Pipeline.enabled == enabled)
        if keyword:
            q = q.where(Pipeline.name.contains(keyword))
        total_q = select(func.count()).select_from(q.subquery())
        total = (await db.execute(total_q)).scalar_one()
        q = q.offset((page - 1) * page_size).limit(page_size).options(
            selectinload(Pipeline.primary_agent),
            selectinload(Pipeline.detection_rules),
        )
        items = (await db.execute(q)).scalars().all()
        return items, total

    async def get(self, db: AsyncSession, pipeline_id: int) -> Pipeline:
        q = select(Pipeline).where(Pipeline.id == pipeline_id).options(
            selectinload(Pipeline.primary_agent),
            selectinload(Pipeline.detection_rules),
        )
        obj = (await db.execute(q)).scalar_one_or_none()
        if not obj:
            raise ResourceNotFound(f"流水线 {pipeline_id} 不存在")
        return obj

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> Pipeline:
        detection_rule_ids: list[int] = data.pop("detection_rule_ids", [])
        sub_agent_ids: list[int] = data.pop("sub_agent_ids", []) or []
        sub_agents_ordered = data.pop("sub_agents_ordered", [])
        if sub_agents_ordered:
            sub_agent_ids = [item["agent_id"] if isinstance(item, dict) else item.agent_id for item in sub_agents_ordered]
        obj = Pipeline(**data)
        if detection_rule_ids:
            rules = (await db.execute(select(DetectionRule).where(DetectionRule.id.in_(detection_rule_ids)))).scalars().all()
            obj.detection_rules = list(rules)
        db.add(obj)
        await db.flush()
        if sub_agent_ids and obj.primary_agent_id is not None:
            primary_agent = (await db.execute(select(Agent).where(Agent.id == obj.primary_agent_id))).scalar_one_or_none()
            if primary_agent:
                primary_agent.sub_agent_ids = sub_agent_ids
        return obj

    async def update(self, db: AsyncSession, pipeline_id: int, data: dict[str, Any]) -> Pipeline:
        obj = await self.get(db, pipeline_id)
        detection_rule_ids: list[int] | None = data.pop("detection_rule_ids", None)
        sub_agent_ids: list[int] | None = data.pop("sub_agent_ids", None)
        sub_agents_ordered = data.pop("sub_agents_ordered", None)
        if sub_agents_ordered is not None:
            sub_agent_ids = [item["agent_id"] if isinstance(item, dict) else item.agent_id for item in sub_agents_ordered]
        for k, v in data.items():
            setattr(obj, k, v)
        if detection_rule_ids is not None:
            rules = (await db.execute(select(DetectionRule).where(DetectionRule.id.in_(detection_rule_ids)))).scalars().all()
            obj.detection_rules = list(rules)
        obj.updated_at = datetime.now(UTC)
        if sub_agent_ids is not None:
            primary_agent_id = obj.primary_agent_id
            if primary_agent_id is not None:
                primary_agent = (await db.execute(select(Agent).where(Agent.id == primary_agent_id))).scalar_one_or_none()
                if primary_agent:
                    primary_agent.sub_agent_ids = sub_agent_ids
        return obj

    async def delete(self, db: AsyncSession, pipeline_id: int) -> None:
        obj = await self.get(db, pipeline_id)
        await db.delete(obj)

    async def toggle(self, db: AsyncSession, pipeline_id: int, enabled: bool) -> Pipeline:
        obj = await self.get(db, pipeline_id)
        obj.enabled = enabled
        obj.updated_at = datetime.now(UTC)
        return obj
