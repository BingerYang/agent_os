from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse
from src.services.detection_service import DetectionService

router = APIRouter()
_svc = DetectionService()


class BindingCreate(BaseModel):
    rule_id: int
    enabled: bool = True
    config_override: dict[str, Any] | None = None
    action_override: str | None = None
    priority_override: int | None = None


class BindingUpdate(BaseModel):
    enabled: bool | None = None
    config_override: dict[str, Any] | None = None
    action_override: str | None = None
    priority_override: int | None = None


class ToggleBody(BaseModel):
    enabled: bool


def _binding_to_dict(obj: Any, rule: Any | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    if rule is not None:
        d["rule_name"] = rule.name
        d["strategy_type"] = rule.strategy_type
        d["stage"] = rule.stage
        merged = dict(rule.rule_content or {})
        if obj.config_override:
            merged.update(obj.config_override)
        d["effective_config"] = merged
        d["effective_action"] = obj.action_override or rule.action_type
        d["effective_priority"] = obj.priority_override if obj.priority_override is not None else rule.priority
    return d


@router.get("/{agent_id}/detection-bindings/summary")
async def get_binding_summary(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    data = await _svc.get_binding_summary(db, agent_id)
    return ApiResponse(data=data)


@router.get("/{agent_id}/detection-bindings")
async def list_bindings(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    bindings = await _svc.get_bindings_for_agent(db, agent_id)
    items = []
    for b in bindings:
        try:
            rule = await _svc.get(db, b.rule_id)
            items.append(_binding_to_dict(b, rule))
        except Exception:
            items.append(_binding_to_dict(b))
    return ApiResponse(data={"agent_id": agent_id, "bindings": items})


@router.post("/{agent_id}/detection-bindings", status_code=201)
async def create_binding(
    agent_id: int,
    body: BindingCreate,
    operator_id: str = Query(default="system"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    obj = await _svc.create_binding(db, agent_id, body.model_dump(exclude_none=True), operator_id=operator_id)
    await db.commit()
    await db.refresh(obj)
    try:
        rule = await _svc.get(db, obj.rule_id)
        return ApiResponse(data=_binding_to_dict(obj, rule))
    except Exception:
        return ApiResponse(data=_binding_to_dict(obj))


@router.put("/{agent_id}/detection-bindings/{binding_id}")
async def update_binding(
    agent_id: int,
    binding_id: int,
    body: BindingUpdate,
    operator_id: str = Query(default="system"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    obj = await _svc.update_binding(db, agent_id, binding_id, body.model_dump(exclude_none=True), operator_id=operator_id)
    await db.commit()
    await db.refresh(obj)
    try:
        rule = await _svc.get(db, obj.rule_id)
        return ApiResponse(data=_binding_to_dict(obj, rule))
    except Exception:
        return ApiResponse(data=_binding_to_dict(obj))


@router.delete("/{agent_id}/detection-bindings/{binding_id}")
async def delete_binding(
    agent_id: int,
    binding_id: int,
    operator_id: str = Query(default="system"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    await _svc.delete_binding(db, agent_id, binding_id, operator_id=operator_id)
    await db.commit()
    return ApiResponse(data=None, message="解绑成功")


@router.patch("/{agent_id}/detection-bindings/{binding_id}/toggle")
async def toggle_binding(
    agent_id: int,
    binding_id: int,
    body: ToggleBody,
    operator_id: str = Query(default="system"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    obj = await _svc.toggle_binding(db, agent_id, binding_id, body.enabled, operator_id=operator_id)
    await db.commit()
    await db.refresh(obj)
    try:
        rule = await _svc.get(db, obj.rule_id)
        return ApiResponse(data=_binding_to_dict(obj, rule))
    except Exception:
        return ApiResponse(data=_binding_to_dict(obj))
