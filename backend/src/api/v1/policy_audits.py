from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse, PageResult
from src.models.policy_config_audit import PolicyConfigAudit

router = APIRouter()


def _to_dict(obj: Any) -> dict[str, Any]:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.get("")
async def list_audits(
    agent_id: int | None = Query(None, description="按 Agent 筛选"),
    rule_id: int | None = Query(None, description="按规则筛选"),
    change_type: str | None = Query(None, description="CREATE/UPDATE/DELETE/ENABLE/DISABLE/BIND/UNBIND"),
    operator_id: str | None = Query(None, description="按操作人筛选"),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    q = select(PolicyConfigAudit)
    if agent_id is not None:
        q = q.where(PolicyConfigAudit.agent_id == agent_id)
    if rule_id is not None:
        q = q.where(PolicyConfigAudit.rule_id == rule_id)
    if change_type:
        q = q.where(PolicyConfigAudit.change_type == change_type)
    if operator_id:
        q = q.where(PolicyConfigAudit.operator_id == operator_id)
    if start_time:
        q = q.where(PolicyConfigAudit.created_at >= start_time)
    if end_time:
        q = q.where(PolicyConfigAudit.created_at <= end_time)
    q = q.order_by(PolicyConfigAudit.created_at.desc())
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(q)).scalars().all()
    return ApiResponse(data=PageResult(
        items=[_to_dict(obj) for obj in items],
        total=total,
        page=page,
        page_size=page_size,
    ))
