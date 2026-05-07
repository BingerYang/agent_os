import time
import uuid as _uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse, PageResult
from src.models.pipeline import Pipeline as _Pipeline
from src.services.agent_service import AgentService

router = APIRouter()
_svc = AgentService()


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    agent_type: str = "SINGLE"
    source_platform: str = "local"
    access_url: str | None = None
    access_token: str | None = None
    llm_model_id: int | None = None
    system_prompt: str | None = None
    status: str = "draft"
    temperature: float = 0.7
    max_tokens: int = 2048
    intent_recognition_enabled: bool = False
    intent_model_id: int | None = None
    intent_confidence_threshold: float = 0.85
    intent_system_prompt: str | None = None
    intent_entity_schema: list | None = None
    routing_strategy: str = "smart"
    routing_model_id: int | None = None
    routing_system_prompt: str | None = None
    routing_threshold: float = 0.8
    routing_intent_rules: list | None = None
    tool_ids: list[int] = []
    skill_ids: list[int] = []
    sub_agent_ids: list[int] = []


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    agent_type: str | None = None
    source_platform: str | None = None
    access_url: str | None = None
    access_token: str | None = None
    llm_model_id: int | None = None
    system_prompt: str | None = None
    status: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    intent_recognition_enabled: bool | None = None
    intent_model_id: int | None = None
    intent_confidence_threshold: float | None = None
    intent_system_prompt: str | None = None
    intent_entity_schema: list | None = None
    routing_strategy: str | None = None
    routing_model_id: int | None = None
    routing_system_prompt: str | None = None
    routing_threshold: float | None = None
    routing_intent_rules: list | None = None
    enabled: bool | None = None
    tool_ids: list[int] | None = None
    skill_ids: list[int] | None = None
    sub_agent_ids: list[int] | None = None


class ToggleBody(BaseModel):
    enabled: bool


class PublishBody(BaseModel):
    status: str


def _to_dict(obj: Any) -> dict:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    d["tool_ids"] = [t.id for t in obj.__dict__.get("tools", [])]
    d["skill_ids"] = [s.id for s in obj.__dict__.get("skills", [])]
    return d


@router.get("")
async def list_agents(
    agent_type: str | None = None,
    enabled: bool | None = None,
    status: str | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> Any:
    from sqlalchemy import select as _sel
    items, total = await _svc.list(
        db,
        agent_type=agent_type,
        enabled=enabled,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    # 批量查询 pipeline_uid
    agent_ids = [item.id for item in items]
    pipeline_uid_map: dict[int, str] = {}
    if agent_ids:
        rows = (
            await db.execute(
                _sel(_Pipeline.primary_agent_id, _Pipeline.uid).where(
                    _Pipeline.primary_agent_id.in_(agent_ids)
                )
            )
        ).all()
        pipeline_uid_map = {row[0]: row[1] for row in rows}

    result_items = []
    for item in items:
        d = _to_dict(item)
        d["pipeline_uid"] = pipeline_uid_map.get(item.id)
        result_items.append(d)

    # status 在内存侧过滤（量小，避免 ORM 改动）
    if status:
        result_items = [i for i in result_items if i.get("status") == status]
        total = len(result_items)

    return ApiResponse.ok(
        PageResult(items=result_items, total=total, page=page, page_size=page_size)
    )


@router.post("")
async def create_agent(body: AgentCreate, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.create(db, body.model_dump())
    return ApiResponse.ok(_to_dict(obj))


@router.get("/{agent_id}")
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.get(db, agent_id)
    return ApiResponse.ok(_to_dict(obj))


@router.put("/{agent_id}")
async def update_agent(agent_id: int, body: AgentUpdate, db: AsyncSession = Depends(get_db)) -> Any:
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    obj = await _svc.update(db, agent_id, data)
    return ApiResponse.ok(_to_dict(obj))


@router.delete("/{agent_id}")
async def delete_agent(agent_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    await _svc.delete(db, agent_id)
    return ApiResponse.ok(None, message="删除成功")


@router.patch("/{agent_id}/toggle")
async def toggle_agent(agent_id: int, body: ToggleBody, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.toggle(db, agent_id, body.enabled)
    return ApiResponse.ok(_to_dict(obj))


@router.patch("/{agent_id}/publish-status")
async def publish_agent_status(agent_id: int, body: PublishBody, db: AsyncSession = Depends(get_db)) -> Any:
    """变更 Agent 状态（published/draft）并维护对应流水线的启用状态。"""
    from sqlalchemy import select as _select

    from src.models.pipeline import Pipeline, PipelineType

    obj = await _svc.publish(db, agent_id, body.status)

    pipeline_uid = None
    if body.status == "published":
        existing = (await db.execute(
            _select(Pipeline).where(Pipeline.primary_agent_id == agent_id)
        )).scalar_one_or_none()

        if existing:
            if not existing.enabled:
                existing.enabled = True
            pipeline_uid = existing.uid
        else:
            pipeline_type = (
                PipelineType.MULTI_AGENT
                if obj.agent_type.value == "ORCHESTRATOR"
                else PipelineType.SINGLE_AGENT
            )
            new_pipeline = Pipeline(
                uid=str(_uuid.uuid4()),
                name=f"{obj.name} 流水线",
                pipeline_type=pipeline_type,
                primary_agent_id=agent_id,
                enabled=True,
            )
            db.add(new_pipeline)
            await db.flush()
            pipeline_uid = new_pipeline.uid
    else:
        existing = (await db.execute(
            _select(Pipeline).where(Pipeline.primary_agent_id == agent_id)
        )).scalar_one_or_none()
        if existing:
            existing.enabled = False
            pipeline_uid = existing.uid

    result = _to_dict(obj)
    result["pipeline_uid"] = pipeline_uid
    return ApiResponse.ok(result)


@router.patch("/{agent_id}/publish")
async def publish_agent_snapshot(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """发布 Agent：生成配置快照写入数据库，并通过 Redis Stream 通知运行时热加载。

    Args:
        agent_id: 要发布的 Agent ID。
        db: 数据库会话。

    Returns:
        ApiResponse[PublishResult]，包含 publish_id、version、redis_notified。
    """
    from src.services.publish_service import publish_agent as _publish

    result = await _publish(db, agent_id)
    return ApiResponse.ok(result.to_dict())


@router.get("/{agent_id}/publishes")
async def list_agent_publishes(
    agent_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """查询 Agent 发布历史记录，按版本号降序分页返回。

    Args:
        agent_id: Agent ID。
        page: 页码（从 1 开始）。
        page_size: 每页条数（最大 100）。
        db: 数据库会话。

    Returns:
        ApiResponse[PageResult[AgentPublish]]。
    """
    from sqlalchemy import func
    from sqlalchemy import select as _select

    from src.models.agent_publish import AgentPublish

    base_q = _select(AgentPublish).where(AgentPublish.agent_id == agent_id)
    total: int = (
        await db.execute(select(func.count()).select_from(base_q.subquery()))
    ).scalar_one()

    result = await db.execute(
        base_q.order_by(AgentPublish.version.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()
    items_data = [
        {
            "id": p.id,
            "agent_id": p.agent_id,
            "version": p.version,
            "is_active": p.is_active,
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "published_by": p.published_by,
        }
        for p in items
    ]
    return ApiResponse.ok(PageResult(items=items_data, total=total, page=page, page_size=page_size))


@router.post("/{agent_id}/ping")
async def ping_agent(agent_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.get(db, agent_id)
    if not obj.access_url:
        return ApiResponse.ok({"reachable": False, "error": "未配置访问地址"})
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(obj.access_url)
        latency_ms = (time.monotonic() - start) * 1000
        return ApiResponse.ok({"reachable": True, "status_code": resp.status_code, "latency_ms": round(latency_ms)})
    except Exception as e:
        latency_ms = (time.monotonic() - start) * 1000
        return ApiResponse.ok({"reachable": False, "error": str(e), "latency_ms": round(latency_ms)})
