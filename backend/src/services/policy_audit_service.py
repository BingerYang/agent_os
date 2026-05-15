from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.policy_config_audit import ChangeType, PolicyConfigAudit


class PolicyAuditService:
    async def record_change(
        self,
        db: AsyncSession,
        *,
        operator_id: str,
        rule_id: int,
        change_type: str,
        agent_id: int | None = None,
        before_value: dict[str, Any] | None = None,
        after_value: dict[str, Any] | None = None,
    ) -> PolicyConfigAudit:
        audit = PolicyConfigAudit(
            operator_id=operator_id,
            rule_id=rule_id,
            change_type=change_type,
            agent_id=agent_id,
            before_value=before_value,
            after_value=after_value,
            created_at=datetime.now(UTC),
        )
        db.add(audit)
        await db.flush()
        return audit


policy_audit_service = PolicyAuditService()
