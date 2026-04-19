from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse, PageResult
from src.services.llm_model_service import LLMModelService, mask_api_key
from pydantic import BaseModel

router = APIRouter()
_svc = LLMModelService()


class ModelCreate(BaseModel):
    name: str
    model_id: str
    supplier: str
    category: str
    endpoint_url: str | None = None
    api_key: str
    api_version: str | None = None
    description: str | None = None


class ModelUpdate(BaseModel):
    name: str | None = None
    supplier: str | None = None
    category: str | None = None
    endpoint_url: str | None = None
    api_key: str | None = None
    api_version: str | None = None
    description: str | None = None
    enabled: bool | None = None


def _mask(obj: Any, supplier: str = "") -> dict:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    d["api_key"] = mask_api_key(d["api_key"], supplier or obj.supplier)
    return d


@router.get("")
async def list_models(
    supplier: str | None = None,
    enabled: bool | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> Any:
    items, total = await _svc.list(db, supplier=supplier, enabled=enabled, keyword=keyword, page=page, page_size=page_size)
    return ApiResponse.ok(PageResult(items=[_mask(i) for i in items], total=total, page=page, page_size=page_size))


@router.post("")
async def create_model(body: ModelCreate, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.create(db, body.model_dump())
    return ApiResponse.ok(_mask(obj))


@router.get("/{model_id}")
async def get_model(model_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.get(db, model_id)
    return ApiResponse.ok(_mask(obj))


@router.put("/{model_id}")
async def update_model(model_id: int, body: ModelUpdate, db: AsyncSession = Depends(get_db)) -> Any:
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    obj = await _svc.update(db, model_id, data)
    return ApiResponse.ok(_mask(obj))


@router.delete("/{model_id}")
async def delete_model(model_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    await _svc.delete(db, model_id)
    return ApiResponse.ok(None, message="删除成功")
