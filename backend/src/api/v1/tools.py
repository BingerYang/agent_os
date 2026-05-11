from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse, PageResult
from src.services.tool_service import ToolService

router = APIRouter()
_svc = ToolService()


class ToolCreate(BaseModel):
    name: str
    display_name: str
    description: str | None = None
    protocol: str
    endpoint_url: str | None = None
    auth_type: str = "NONE"
    auth_config: dict | None = None
    headers: dict | None = None
    input_schema: dict = {}
    output_schema: dict | None = None
    source_platform: str = "local"
    tags: list | None = None
    version: str = "v1.0.0"


class ToolUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    protocol: str | None = None
    endpoint_url: str | None = None
    auth_type: str | None = None
    auth_config: dict | None = None
    headers: dict | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    tags: list | None = None
    version: str | None = None
    enabled: bool | None = None


class ToggleBody(BaseModel):
    enabled: bool


def _base_to_dict(obj: Any) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def _tool_to_dict(obj: Any) -> dict:
    data = _base_to_dict(obj)
    if obj.mcp_server:
        data["mcp_server_name"] = obj.mcp_server.name
    return data


@router.get("")
async def list_tools(
    protocol: str | None = None,
    enabled: bool | None = None,
    keyword: str | None = None,
    mcp_server_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> Any:
    items, total = await _svc.list(
        db,
        protocol=protocol,
        enabled=enabled,
        keyword=keyword,
        mcp_server_id=mcp_server_id,
        page=page,
        page_size=page_size,
    )
    return ApiResponse.ok(
        PageResult(items=[_tool_to_dict(i) for i in items], total=total, page=page, page_size=page_size)
    )


@router.post("")
async def create_tool(body: ToolCreate, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.create(db, body.model_dump())
    return ApiResponse.ok(_tool_to_dict(obj))


@router.get("/{tool_id}")
async def get_tool(tool_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.get(db, tool_id)
    return ApiResponse.ok(_tool_to_dict(obj))


@router.put("/{tool_id}")
async def update_tool(tool_id: int, body: ToolUpdate, db: AsyncSession = Depends(get_db)) -> Any:
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    obj = await _svc.update(db, tool_id, data)
    return ApiResponse.ok(_tool_to_dict(obj))


@router.delete("/{tool_id}")
async def delete_tool(tool_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    await _svc.delete(db, tool_id)
    return ApiResponse.ok(None, message="删除成功")


@router.patch("/{tool_id}/toggle")
async def toggle_tool(tool_id: int, body: ToggleBody, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.toggle(db, tool_id, body.enabled)
    return ApiResponse.ok(_tool_to_dict(obj))
