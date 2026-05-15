from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ResourceNotFound
from src.models.detection_event import DetectionEvent, EventStatus


class DetectionEventService:
    async def record_event(
        self,
        db: AsyncSession,
        *,
        agent_id: int,
        rule_id: int | None = None,
        session_id: str | None = None,
        stage: str,
        strategy_type: str,
        action_taken: str,
        hit_detail: dict[str, Any] | None = None,
        input_snapshot: str | None = None,
        output_snapshot: str | None = None,
        status: str = EventStatus.LOGGED,
    ) -> DetectionEvent:
        obj = DetectionEvent(
            agent_id=agent_id,
            rule_id=rule_id,
            session_id=session_id,
            stage=stage,
            strategy_type=strategy_type,
            action_taken=action_taken,
            hit_detail=hit_detail,
            input_snapshot=input_snapshot[:500] if input_snapshot else None,
            output_snapshot=output_snapshot[:500] if output_snapshot else None,
            status=status,
        )
        db.add(obj)
        await db.flush()
        return obj

    async def list_events(
        self,
        db: AsyncSession,
        *,
        agent_id: int | None = None,
        strategy_type: str | None = None,
        action_taken: str | None = None,
        status: str | None = None,
        stage: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[DetectionEvent], int]:
        q = select(DetectionEvent)
        if agent_id is not None:
            q = q.where(DetectionEvent.agent_id == agent_id)
        if strategy_type:
            q = q.where(DetectionEvent.strategy_type == strategy_type)
        if action_taken:
            q = q.where(DetectionEvent.action_taken == action_taken)
        if status:
            q = q.where(DetectionEvent.status == status)
        if stage:
            q = q.where(DetectionEvent.stage == stage)
        if start_time:
            q = q.where(DetectionEvent.created_at >= start_time)
        if end_time:
            q = q.where(DetectionEvent.created_at <= end_time)
        q = q.order_by(DetectionEvent.created_at.desc())
        total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        q = q.offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(q)).scalars().all()
        return items, total

    async def get_event(self, db: AsyncSession, event_id: int) -> DetectionEvent:
        obj = await db.get(DetectionEvent, event_id)
        if not obj:
            raise ResourceNotFound(f"DetectionEvent {event_id} 不存在")
        return obj

    async def review_event(
        self,
        db: AsyncSession,
        event_id: int,
        *,
        status: str,
        reviewer_id: str,
        reviewer_note: str | None = None,
    ) -> DetectionEvent:
        obj = await self.get_event(db, event_id)
        if obj.status not in (EventStatus.PENDING_REVIEW, EventStatus.ESCALATED):
            raise ValueError(f"事件状态 {obj.status} 不可复核")
        obj.status = status
        obj.reviewer_id = reviewer_id
        obj.reviewer_note = reviewer_note
        obj.reviewed_at = datetime.now(UTC)
        if obj.strategy_type == "human_approval":
            try:
                from src.agents.detection_approval import resolve_approval
                resolve_approval(obj.id, approved=(status == EventStatus.REVIEWED))
            except Exception:
                pass
        return obj


detection_event_service = DetectionEventService()
