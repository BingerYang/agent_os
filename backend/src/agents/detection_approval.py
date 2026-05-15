"""
A-03 人机审批异步队列（响应级审批）。
Agent 产生最终响应后、返回给用户前，挂起等待审批员通过 Web 端决策。
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ApprovalEntry:
    event_id: int
    event: asyncio.Event = field(default_factory=asyncio.Event)
    approved: bool = False
    rejection_reason: str | None = None


class ApprovalQueue:
    """内存审批队列：每条待审批响应对应一个 ApprovalEntry。"""

    def __init__(self) -> None:
        self._entries: dict[int, ApprovalEntry] = {}

    def create_entry(self, event_id: int) -> ApprovalEntry:
        entry = ApprovalEntry(event_id=event_id)
        self._entries[event_id] = entry
        logger.info("ApprovalQueue: created entry event_id=%d", event_id)
        return entry

    async def wait_for_approval(self, event_id: int, timeout_seconds: float = 300.0) -> bool:
        entry = self._entries.get(event_id)
        if entry is None:
            logger.warning("ApprovalQueue: entry %d not found", event_id)
            return False
        try:
            await asyncio.wait_for(entry.event.wait(), timeout=timeout_seconds)
            return entry.approved
        except asyncio.TimeoutError:
            logger.warning(
                "ApprovalQueue: event_id=%d timed out after %.0fs", event_id, timeout_seconds
            )
            self._entries.pop(event_id, None)
            return False

    def resolve(
        self, event_id: int, approved: bool, rejection_reason: str | None = None
    ) -> bool:
        entry = self._entries.get(event_id)
        if entry is None:
            return False
        entry.approved = approved
        entry.rejection_reason = rejection_reason
        entry.event.set()
        logger.info("ApprovalQueue: resolved event_id=%d approved=%s", event_id, approved)
        return True

    def discard(self, event_id: int) -> None:
        self._entries.pop(event_id, None)


approval_queue = ApprovalQueue()


async def create_approval_event(
    db: Any,
    *,
    agent_id: int,
    rule_id: int | None,
    session_id: str | None,
    input_snapshot: str,
    output_snapshot: str,
    timeout_seconds: float = 300.0,
    fallback_action: str = "block",
) -> dict[str, Any]:
    """
    将响应写入 ESCALATED 状态的 DetectionEvent，并在审批队列中注册等待 entry。
    返回 {event_id, timeout_seconds, fallback_action}。
    """
    from src.models.detection_event import DetectionEvent, EventStatus

    event = DetectionEvent(
        agent_id=agent_id,
        rule_id=rule_id,
        session_id=session_id,
        stage="POST",
        strategy_type="human_approval",
        action_taken="escalate",
        input_snapshot=input_snapshot[:500] if input_snapshot else None,
        output_snapshot=output_snapshot[:500] if output_snapshot else None,
        status=EventStatus.ESCALATED,
    )
    db.add(event)
    await db.flush()

    approval_queue.create_entry(event.id)
    return {
        "event_id": event.id,
        "timeout_seconds": timeout_seconds,
        "fallback_action": fallback_action,
    }


async def wait_for_approval(event_id: int, timeout_seconds: float = 300.0) -> bool:
    """等待审批结果，超时返回 False。"""
    return await approval_queue.wait_for_approval(event_id, timeout_seconds)


def resolve_approval(event_id: int, approved: bool, rejection_reason: str | None = None) -> bool:
    """由审批员调用，通知等待方审批结果。"""
    return approval_queue.resolve(event_id, approved, rejection_reason)
