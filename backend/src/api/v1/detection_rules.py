from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse, PageResult
from src.services.detection_service import DetectionService

router = APIRouter()
_svc = DetectionService()


class DetectionRuleCreate(BaseModel):
    name: str
    stage: str
    rule_type: str
    rule_content: dict
    reject_message: str | None = None
    priority: int = 100


class DetectionRuleUpdate(BaseModel):
    name: str | None = None
    stage: str | None = None
    rule_type: str | None = None
    rule_content: dict | None = None
    reject_message: str | None = None
    priority: int | None = None
    enabled: bool | None = None


class ToggleBody(BaseModel):
    enabled: bool


def _to_dict(obj: Any) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.get("")
async def list_rules(
    stage: str | None = None,
    rule_type: str | None = None,
    enabled: bool | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> Any:
    items, total = await _svc.list(db, stage=stage, rule_type=rule_type, enabled=enabled, keyword=keyword, page=page, page_size=page_size)
    return ApiResponse.ok(PageResult(items=[_to_dict(i) for i in items], total=total, page=page, page_size=page_size))


@router.post("")
async def create_rule(body: DetectionRuleCreate, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.create(db, body.model_dump())
    return ApiResponse.ok(_to_dict(obj))


@router.get("/{rule_id}")
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.get(db, rule_id)
    return ApiResponse.ok(_to_dict(obj))


@router.put("/{rule_id}")
async def update_rule(rule_id: int, body: DetectionRuleUpdate, db: AsyncSession = Depends(get_db)) -> Any:
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    obj = await _svc.update(db, rule_id, data)
    return ApiResponse.ok(_to_dict(obj))


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    await _svc.delete(db, rule_id)
    return ApiResponse.ok(None, message="删除成功")


@router.patch("/{rule_id}/toggle")
async def toggle_rule(rule_id: int, body: ToggleBody, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.toggle(db, rule_id, body.enabled)
    return ApiResponse.ok(_to_dict(obj))
