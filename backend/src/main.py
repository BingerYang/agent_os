"""单体应用入口（本地开发 / 单进程部署）。

包含全部管理路由 + 对话路由，lifespan 同时完成数据库初始化和运行时上下文加载。
生产分离部署请分别使用 main_management.py 和 main_runtime.py。
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.database import init_db
from src.core.middleware import RequestLoggingMiddleware, register_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """单体应用生命周期：DB 初始化 + 运行时上下文加载 + Redis 订阅。"""
    from src.core.database import AsyncSessionLocal
    from src.runtime.loader import load_from_db, start_redis_subscriber, stop_redis_subscriber

    settings = get_settings()

    # 1. 初始化数据库表结构
    await init_db()

    # 2. 全量加载运行时上下文（失败则启动失败，Fail Fast）
    try:
        async with AsyncSessionLocal() as db:
            context = await load_from_db(db)
        app.state.runtime_context = context
        logger.info("main.runtime_context_loaded agents=%d", context.agent_pool.size())
    except Exception as exc:
        logger.warning("main.runtime_context_load_failed error=%s — 对话功能不可用", exc)
        app.state.runtime_context = None

    # 3. 启动 Redis 热更新订阅（上下文加载成功才启动）
    redis_task = None
    if app.state.runtime_context is not None:
        redis_task = start_redis_subscriber(
            context=app.state.runtime_context,
            stream_key=settings.redis_stream_key,
        )
        app.state.redis_task = redis_task

    yield

    # 4. 关闭 Redis 订阅
    if redis_task is not None:
        stop_redis_subscriber(redis_task)

    # 5. 关闭 MCP 长连接
    if app.state.runtime_context is not None:
        await app.state.runtime_context.mcp_pool.close_all()


def create_app() -> FastAPI:
    """构建单体 FastAPI 应用（包含管理端 + 运行时路由）。"""
    settings = get_settings()
    app = FastAPI(
        title="Agent 调度平台",
        description="可配置可扩展智能体编排系统 API",
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

    from src.api.v1.router import api_router
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict:
        context = getattr(app.state, "runtime_context", None)
        redis_task = getattr(app.state, "redis_task", None)
        return {
            "status": "ok",
            "agents_loaded": context.agent_pool.size() if context else 0,
            "redis_subscribed": redis_task is not None and not redis_task.done(),
        }

    return app


app = create_app()
