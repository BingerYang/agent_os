from typing import Any
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse, PageResult
from src.services.pipeline_service import PipelineService

router = APIRouter()
_svc = PipelineService()


class SubAgentOrderItem(BaseModel):
    agent_id: int
    order_index: int = 0


class PipelineCreate(BaseModel):
    name: str
    primary_agent_id: int | None = None
    route_confidence_threshold: float = 0.7
    timeout_seconds: int = 30
    stream_output: bool = False
    detection_rule_ids: list[int] = []
    sub_agent_ids: list[int] = []
    sub_agents_ordered: list[SubAgentOrderItem] = []


class PipelineUpdate(BaseModel):
    name: str | None = None
    primary_agent_id: int | None = None
    route_confidence_threshold: float | None = None
    timeout_seconds: int | None = None
    stream_output: bool | None = None
    enabled: bool | None = None
    detection_rule_ids: list[int] | None = None
    sub_agent_ids: list[int] | None = None
    sub_agents_ordered: list[SubAgentOrderItem] | None = None


class ToggleBody(BaseModel):
    enabled: bool


def _to_dict(obj: Any) -> dict:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    d["detection_rule_ids"] = [r.id for r in obj.__dict__.get("detection_rules", [])]
    primary_agent = obj.__dict__.get("primary_agent")
    d["sub_agent_ids"] = list(primary_agent.sub_agent_ids or []) if primary_agent else []
    return d


@router.get("")
async def list_pipelines(
    pipeline_type: str | None = None,
    enabled: bool | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> Any:
    items, total = await _svc.list(db, pipeline_type=pipeline_type, enabled=enabled, keyword=keyword, page=page, page_size=page_size)
    return ApiResponse.ok(PageResult(items=[_to_dict(i) for i in items], total=total, page=page, page_size=page_size))


@router.post("")
async def create_pipeline(body: PipelineCreate, db: AsyncSession = Depends(get_db)) -> Any:
    data = body.model_dump()
    data["pipeline_type"] = "MULTI_AGENT" if data.get("sub_agent_ids") else "SINGLE_AGENT"
    obj = await _svc.create(db, data)
    await db.refresh(obj, attribute_names=["primary_agent", "detection_rules"])
    return ApiResponse.ok(_to_dict(obj))


@router.get("/{pipeline_id}")
async def get_pipeline(pipeline_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.get(db, pipeline_id)
    return ApiResponse.ok(_to_dict(obj))


@router.put("/{pipeline_id}")
async def update_pipeline(pipeline_id: int, body: PipelineUpdate, db: AsyncSession = Depends(get_db)) -> Any:
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if "sub_agent_ids" in data:
        data["pipeline_type"] = "MULTI_AGENT" if data["sub_agent_ids"] else "SINGLE_AGENT"
    obj = await _svc.update(db, pipeline_id, data)
    await db.refresh(obj, attribute_names=["primary_agent", "detection_rules"])
    return ApiResponse.ok(_to_dict(obj))


@router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    await _svc.delete(db, pipeline_id)
    return ApiResponse.ok(None, message="删除成功")


@router.patch("/{pipeline_id}/toggle")
async def toggle_pipeline(pipeline_id: int, body: ToggleBody, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.toggle(db, pipeline_id, body.enabled)
    return ApiResponse.ok(_to_dict(obj))
