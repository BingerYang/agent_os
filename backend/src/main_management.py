"""管理端 FastAPI 应用入口。

包含所有 CRUD 管理路由，不含对话（query）路由。
独立启动命令：uvicorn src.main_management:app --reload
生产分离部署时配合 nginx 使用，对话请求由 nginx 路由到 main_runtime。
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.database import init_db
from src.core.middleware import RequestLoggingMiddleware, register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """管理端生命周期：仅初始化数据库表结构。"""
    await init_db()
    yield


def create_management_app() -> FastAPI:
    """构建管理端 FastAPI 应用。

    Returns:
        配置好 CORS、中间件、异常处理和所有管理端路由的 FastAPI 实例。
    """
    settings = get_settings()
    app = FastAPI(
        title="Agent 调度平台 - 管理端",
        description="Agent / Tool / Skill / Pipeline 等资源的 CRUD 管理接口",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    # 注册所有管理端路由（不含 query）
    from fastapi import APIRouter

    from src.api.v1 import (
        agents,
        detection_rules,
        events,
        marketplace,
        mcp_servers,
        models_config,
        pipelines,
        skills,
        tools,
    )

    mgmt_router = APIRouter()
    mgmt_router.include_router(mcp_servers.router, prefix="/mcp-servers", tags=["MCP Server 管理"])
    mgmt_router.include_router(models_config.router, prefix="/models", tags=["模型配置"])
    mgmt_router.include_router(models_config.router, prefix="/models-config", tags=["模型配置"])
    mgmt_router.include_router(tools.router, prefix="/tools", tags=["工具管理"])
    mgmt_router.include_router(skills.router, prefix="/skills", tags=["技能管理"])
    mgmt_router.include_router(agents.router, prefix="/agents", tags=["Agent 管理"])
    mgmt_router.include_router(pipelines.router, prefix="/pipelines", tags=["流水线管理"])
    mgmt_router.include_router(detection_rules.router, prefix="/detection-rules", tags=["检测规则"])
    mgmt_router.include_router(marketplace.router, prefix="/marketplace", tags=["Marketplace"])
    mgmt_router.include_router(events.router, prefix="", tags=["事件流"])

    app.include_router(mgmt_router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_management_app()
