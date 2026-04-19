from typing import Any
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse
from src.services.marketplace_service import MarketplaceService

router = APIRouter()
_svc = MarketplaceService()


class RegisterAgentBody(BaseModel):
    name: str
    access_url: str
    access_token: str
    description: str = ""


@router.get("")
async def list_marketplace(
    item_type: str | None = None,
    enabled: bool | None = None,
    keyword: str | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    items = await _svc.get_marketplace_items(
        db,
        item_type=item_type,
        enabled=enabled,
        keyword=keyword,
        tag=tag,
    )
    return ApiResponse.ok({"items": items, "total": len(items)})


@router.post("/{item_type}/{item_id}/install")
async def install_item(item_type: str, item_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    result = await _svc.install_item(db, item_type, item_id)
    return ApiResponse.ok(result)


@router.delete("/{item_type}/{item_id}/install")
async def uninstall_item(item_type: str, item_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    result = await _svc.uninstall_item(db, item_type, item_id)
    return ApiResponse.ok(result)


@router.post("/agents")
async def register_agent(body: RegisterAgentBody, db: AsyncSession = Depends(get_db)) -> Any:
    try:
        agent = await _svc.register_third_party_agent(
            db,
            name=body.name,
            access_url=body.access_url,
            access_token=body.access_token,
            description=body.description,
        )
    except ValueError:
        return JSONResponse(
            status_code=400,
            content=ApiResponse.error(400, "访问地址不可达").model_dump(mode="json"),
        )

    return ApiResponse.ok({"id": agent.id, "name": agent.name, "access_url": agent.access_url})
