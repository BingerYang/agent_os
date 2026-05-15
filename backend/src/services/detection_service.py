from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ResourceNotFound
from src.models.agent_detection_binding import AgentDetectionBinding
from src.models.detection_rule import DetectionRule
from src.services.config_cache import _serialize_model
from src.services.event_bus import event_bus
from src.services.policy_audit_service import policy_audit_service


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


class DetectionService:
    async def list(
        self,
        db: AsyncSession,
        stage: str | None = None,
        rule_type: str | None = None,
        strategy_type: str | None = None,
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
        if strategy_type:
            q = q.where(DetectionRule.strategy_type == strategy_type)
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
        obj.updated_at = datetime.now(UTC)
        return obj

    async def delete(self, db: AsyncSession, rule_id: int) -> None:
        obj = await self.get(db, rule_id)
        await db.delete(obj)
        await event_bus.publish(_build_event("detection_rule", obj.id, "delete"))

    async def toggle(self, db: AsyncSession, rule_id: int, enabled: bool) -> DetectionRule:
        obj = await self.get(db, rule_id)
        obj.enabled = enabled
        obj.updated_at = datetime.now(UTC)
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
                DetectionRule.enabled,
            )
            .order_by(DetectionRule.priority.asc())
        )
        return (await db.execute(q)).scalars().all()

    async def get_bindings_for_agent(
        self,
        db: AsyncSession,
        agent_id: int,
    ) -> Sequence[AgentDetectionBinding]:
        q = (
            select(AgentDetectionBinding)
            .where(AgentDetectionBinding.agent_id == agent_id)
            .order_by(AgentDetectionBinding.id.asc())
        )
        return (await db.execute(q)).scalars().all()

    async def get_binding(
        self,
        db: AsyncSession,
        agent_id: int,
        binding_id: int,
    ) -> AgentDetectionBinding:
        obj = await db.get(AgentDetectionBinding, binding_id)
        if not obj or obj.agent_id != agent_id:
            raise ResourceNotFound(f"AgentDetectionBinding {binding_id} not found")
        return obj

    async def create_binding(
        self,
        db: AsyncSession,
        agent_id: int,
        data: dict[str, Any],
        operator_id: str = "system",
    ) -> AgentDetectionBinding:
        obj = AgentDetectionBinding(agent_id=agent_id, **data)
        db.add(obj)
        await db.flush()
        rule = await self.get(db, obj.rule_id)
        from src.models.policy_config_audit import ChangeType

        await policy_audit_service.record_change(
            db,
            operator_id=operator_id,
            rule_id=rule.id,
            change_type=ChangeType.BIND,
            agent_id=agent_id,
            after_value=_serialize_model(obj),
        )
        return obj

    async def update_binding(
        self,
        db: AsyncSession,
        agent_id: int,
        binding_id: int,
        data: dict[str, Any],
        operator_id: str = "system",
    ) -> AgentDetectionBinding:
        obj = await self.get_binding(db, agent_id, binding_id)
        before_value = _serialize_model(obj)
        for k, v in data.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.now(UTC)
        from src.models.policy_config_audit import ChangeType

        await policy_audit_service.record_change(
            db,
            operator_id=operator_id,
            rule_id=obj.rule_id,
            change_type=ChangeType.UPDATE,
            agent_id=agent_id,
            before_value=before_value,
            after_value=_serialize_model(obj),
        )
        return obj

    async def delete_binding(
        self,
        db: AsyncSession,
        agent_id: int,
        binding_id: int,
        operator_id: str = "system",
    ) -> None:
        obj = await self.get_binding(db, agent_id, binding_id)
        from src.models.policy_config_audit import ChangeType

        await policy_audit_service.record_change(
            db,
            operator_id=operator_id,
            rule_id=obj.rule_id,
            change_type=ChangeType.UNBIND,
            agent_id=agent_id,
            before_value=_serialize_model(obj),
        )
        await db.delete(obj)

    async def toggle_binding(
        self,
        db: AsyncSession,
        agent_id: int,
        binding_id: int,
        enabled: bool,
        operator_id: str = "system",
    ) -> AgentDetectionBinding:
        obj = await self.get_binding(db, agent_id, binding_id)
        before_value = _serialize_model(obj)
        obj.enabled = enabled
        obj.updated_at = datetime.now(UTC)
        from src.models.policy_config_audit import ChangeType

        await policy_audit_service.record_change(
            db,
            operator_id=operator_id,
            rule_id=obj.rule_id,
            change_type=ChangeType.ENABLE if enabled else ChangeType.DISABLE,
            agent_id=agent_id,
            before_value=before_value,
            after_value=_serialize_model(obj),
        )
        return obj

    async def get_rules_for_agent(
        self,
        db: AsyncSession,
        agent_id: int,
        stage: str,
    ) -> list[dict[str, Any]]:
        bindings = await self.get_bindings_for_agent(db, agent_id)
        items: list[dict[str, Any]] = []
        for b in bindings:
            if not b.enabled:
                continue
            try:
                rule = await self.get(db, b.rule_id)
            except ResourceNotFound:
                continue
            if not rule.enabled or rule.stage != stage:
                continue
            merged_config = dict(rule.rule_content or {})
            if b.config_override:
                merged_config.update(b.config_override)
            effective_action = b.action_override or rule.action_type
            effective_priority = b.priority_override if b.priority_override is not None else rule.priority
            items.append(
                {
                    "binding_id": b.id,
                    "rule_id": rule.id,
                    "rule": _serialize_model(rule),
                    "merged_config": merged_config,
                    "effective_action": effective_action,
                    "effective_priority": effective_priority,
                }
            )
        items.sort(key=lambda item: item["effective_priority"])
        return items

    async def get_binding_summary(
        self,
        db: AsyncSession,
        agent_id: int,
    ) -> dict[str, Any]:
        from src.api.v1.detection_rules import _STRATEGY_META

        bindings = await self.get_bindings_for_agent(db, agent_id)
        binding_map = {binding.rule_id: binding for binding in bindings}

        async def _build_entry(meta: dict[str, Any]) -> dict[str, Any]:
            q = (
                select(DetectionRule)
                .where(
                    DetectionRule.strategy_type == meta["value"],
                    DetectionRule.stage == meta["stage"],
                    DetectionRule.enabled,
                )
                .limit(1)
            )
            rule = (await db.execute(q)).scalars().first()
            binding = binding_map.get(rule.id) if rule else None
            return {
                "strategy_type": meta["value"],
                "name": meta["label"],
                "enabled": bool(binding and binding.enabled),
                "binding_id": binding.id if binding else None,
                "rule_id": rule.id if rule else None,
            }

        pre_checks = [await _build_entry(meta) for meta in _STRATEGY_META if meta["stage"] == "PRE"]
        post_checks = [await _build_entry(meta) for meta in _STRATEGY_META if meta["stage"] == "POST"]
        return {"pre_checks": pre_checks, "post_checks": post_checks}
