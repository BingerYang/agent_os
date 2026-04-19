from __future__ import annotations
from collections.abc import Sequence

import builtins
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ResourceNotFound
from src.models.detection_rule import DetectionRule
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


class DetectionService:
    async def list(
        self,
        db: AsyncSession,
        stage: str | None = None,
        rule_type: str | None = None,
        enabled: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[DetectionRule], int]:
        q = select(DetectionRule)
        if stage:
            q = q.where(DetectionRule.stage == stage)
        if rule_type:
            q = q.where(DetectionRule.rule_type == rule_type)
        if enabled is not None:
            q = q.where(DetectionRule.enabled == enabled)
        if keyword:
            q = q.where(DetectionRule.name.contains(keyword))
        q = q.order_by(DetectionRule.priority.asc())
        total_q = select(func.count()).select_from(q.subquery())
        total = (await db.execute(total_q)).scalar_one()
        q = q.offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(q)).scalars().all()
        return items, total

    async def get(self, db: AsyncSession, rule_id: int) -> DetectionRule:
        obj = await db.get(DetectionRule, rule_id)
        if not obj:
            raise ResourceNotFound(f"检测规则 {rule_id} 不存在")
        return obj

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> DetectionRule:
        obj = DetectionRule(**data)
        db.add(obj)
        await db.flush()
        await event_bus.publish(_build_event("detection_rule", obj.id, "create", _serialize_model(obj)))
        return obj

    async def update(self, db: AsyncSession, rule_id: int, data: dict[str, Any]) -> DetectionRule:
        obj = await self.get(db, rule_id)
        for k, v in data.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.now(timezone.utc)
        return obj

    async def delete(self, db: AsyncSession, rule_id: int) -> None:
        obj = await self.get(db, rule_id)
        await db.delete(obj)
        await event_bus.publish(_build_event("detection_rule", obj.id, "delete"))

    async def toggle(self, db: AsyncSession, rule_id: int, enabled: bool) -> DetectionRule:
        obj = await self.get(db, rule_id)
        obj.enabled = enabled
        obj.updated_at = datetime.now(timezone.utc)
        await event_bus.publish(
            _build_event(
                "detection_rule",
                obj.id,
                "enable" if enabled else "disable",
                _serialize_model(obj) if enabled else None,
            )
        )
        return obj

    async def get_rules_for_pipeline(
        self,
        db: AsyncSession,
        pipeline_id: int,
        stage: str,
    ) -> Sequence[DetectionRule]:
        from src.models.associations import pipeline_detection_rules

        q = (
            select(DetectionRule)
            .join(pipeline_detection_rules, DetectionRule.id == pipeline_detection_rules.c.rule_id)
            .where(
                pipeline_detection_rules.c.pipeline_id == pipeline_id,
                DetectionRule.stage == stage,
                DetectionRule.enabled == True,
            )
            .order_by(DetectionRule.priority.asc())
        )
        return (await db.execute(q)).scalars().all()
