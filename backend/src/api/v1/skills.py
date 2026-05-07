from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse, PageResult
from src.services.skill_service import SkillService

router = APIRouter()
_svc = SkillService()


class SkillCreate(BaseModel):
    name: str
    description: str | None = None
    trigger_condition: str | None = None
    tags: list | None = None
    version: str = "v1.0.0"
    category: str = "general"
    author: str = "系统官方"
    tool_ids: list[int] = []


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger_condition: str | None = None
    tags: list | None = None
    version: str | None = None
    category: str | None = None
    author: str | None = None
    enabled: bool | None = None
    tool_ids: list[int] | None = None


class ToggleBody(BaseModel):
    enabled: bool


def _to_dict(obj: Any) -> dict:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    d["tool_ids"] = [t.id for t in obj.__dict__.get("tools", [])]
    return d


@router.get("")
async def list_skills(
    enabled: bool | None = None,
    keyword: str | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> Any:
    items, total = await _svc.list(db, enabled=enabled, keyword=keyword, category=category, page=page, page_size=page_size)
    return ApiResponse.ok(PageResult(items=[_to_dict(i) for i in items], total=total, page=page, page_size=page_size))


@router.post("")
async def create_skill(body: SkillCreate, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.create(db, body.model_dump())
    return ApiResponse.ok(_to_dict(obj))


@router.get("/{skill_id}")
async def get_skill(skill_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.get(db, skill_id)
    return ApiResponse.ok(_to_dict(obj))


@router.put("/{skill_id}")
async def update_skill(skill_id: int, body: SkillUpdate, db: AsyncSession = Depends(get_db)) -> Any:
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    obj = await _svc.update(db, skill_id, data)
    return ApiResponse.ok(_to_dict(obj))


@router.delete("/{skill_id}")
async def delete_skill(skill_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    await _svc.delete(db, skill_id)
    return ApiResponse.ok(None, message="删除成功")


@router.patch("/{skill_id}/toggle")
async def toggle_skill(skill_id: int, body: ToggleBody, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.toggle(db, skill_id, body.enabled)
    return ApiResponse.ok(_to_dict(obj))
