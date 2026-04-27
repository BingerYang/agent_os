from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse, PageResult
from src.services.mcp_server_service import MCPServerService

router = APIRouter()
_svc = MCPServerService()


class MCPServerCreate(BaseModel):
    name: str
    display_name: str
    description: str | None = None
    transport_type: str = "HTTP_SSE"
    command: str | None = None
    args: list | None = None
    env_vars: dict | None = None
    endpoint_url: str | None = None
    auth_type: str = "NONE"
    auth_config: dict | None = None
    enabled: bool = True


class MCPServerUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    transport_type: str | None = None
    command: str | None = None
    args: list | None = None
    env_vars: dict | None = None
    endpoint_url: str | None = None
    auth_type: str | None = None
    auth_config: dict | None = None
    enabled: bool | None = None


class ToggleBody(BaseModel):
    enabled: bool


def _to_dict(obj: Any) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


@router.get("")
async def list_mcp_servers(
    keyword: str | None = None,
    enabled: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> Any:
    items, total = await _svc.list(db, keyword=keyword, enabled=enabled, page=page, page_size=page_size)
    return ApiResponse.ok(PageResult(items=[_to_dict(i) for i in items], total=total, page=page, page_size=page_size))


@router.post("")
async def create_mcp_server(body: MCPServerCreate, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.create(db, body.model_dump())
    return ApiResponse.ok(_to_dict(obj))


@router.get("/{server_id}")
async def get_mcp_server(server_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.get(db, server_id)
    return ApiResponse.ok(_to_dict(obj))


@router.put("/{server_id}")
async def update_mcp_server(server_id: int, body: MCPServerUpdate, db: AsyncSession = Depends(get_db)) -> Any:
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    obj = await _svc.update(db, server_id, data)
    return ApiResponse.ok(_to_dict(obj))


@router.delete("/{server_id}")
async def delete_mcp_server(server_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    await _svc.delete(db, server_id)
    return ApiResponse.ok(None, message="删除成功")


@router.patch("/{server_id}/toggle")
async def toggle_mcp_server(server_id: int, body: ToggleBody, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.toggle(db, server_id, body.enabled)
    return ApiResponse.ok(_to_dict(obj))


@router.post("/{server_id}/connect")
async def connect_mcp_server(server_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    result = await _svc.connect(db, server_id)
    return ApiResponse.ok(result)


@router.post("/{server_id}/discover")
async def discover_tools(server_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    result = await _svc.discover_tools(db, server_id)
    return ApiResponse.ok(result)
