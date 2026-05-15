from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse, PageResult
from src.services.detection_event_service import detection_event_service

router = APIRouter()


def _to_dict(obj: Any) -> dict[str, Any]:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


class ReviewBody(BaseModel):
    status: str
    reviewer_note: str | None = None


@router.get("")
async def list_events(
    agent_id: int | None = Query(None),
    strategy_type: str | None = Query(None),
    action_taken: str | None = Query(None),
    status: str | None = Query(None),
    stage: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    items, total = await detection_event_service.list_events(
        db,
        agent_id=agent_id,
        strategy_type=strategy_type,
        action_taken=action_taken,
        status=status,
        stage=stage,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResult(
        items=[_to_dict(obj) for obj in items],
        total=total,
        page=page,
        page_size=page_size,
    ))


@router.get("/{event_id}")
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)) -> ApiResponse:
    obj = await detection_event_service.get_event(db, event_id)
    return ApiResponse(data=_to_dict(obj))


@router.patch("/{event_id}/review")
async def review_event(
    event_id: int,
    body: ReviewBody,
    reviewer_id: str = Query(default="system"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    obj = await detection_event_service.review_event(
        db,
        event_id,
        status=body.status,
        reviewer_id=reviewer_id,
        reviewer_note=body.reviewer_note,
    )
    await db.commit()
    await db.refresh(obj)
    return ApiResponse(data=_to_dict(obj))
