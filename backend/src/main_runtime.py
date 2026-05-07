"""运行时 FastAPI 应用入口。

仅包含对话（query）路由，启动时从 DB 全量加载 Agent 配置并订阅 Redis Stream。
独立启动命令：uvicorn src.main_runtime:app --reload
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.middleware import RequestLoggingMiddleware, register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """运行时生命周期：DB 全量加载 + Redis Stream 订阅。

    启动时：
    1. 从 DB 全量加载已发布 Agent 到内存池（DB 不可用则启动失败）。
    2. 启动 Redis Stream 后台订阅 Task。

    关闭时：
    3. 取消 Redis 订阅 Task。
    4. 关闭所有 MCP 长连接。
    """
    from src.core.database import AsyncSessionLocal
    from src.runtime.loader import load_from_db, start_redis_subscriber, stop_redis_subscriber

    settings = get_settings()

    # 1. 全量加载（DB 不可用则抛出异常，不降级）
    async with AsyncSessionLocal() as db:
        context = await load_from_db(db)

    # 2. 将 context 挂载到 app.state 供路由使用
    app.state.runtime_context = context

    # 3. 启动 Redis 后台订阅
    redis_task = start_redis_subscriber(
        context=context,
        stream_key=settings.redis_stream_key,
    )
    app.state.redis_task = redis_task

    yield

    # 4. 关闭 Redis 订阅
    stop_redis_subscriber(redis_task)

    # 5. 关闭 MCP 长连接
    await context.mcp_pool.close_all()


def create_runtime_app() -> FastAPI:
    """构建运行时 FastAPI 应用。

    Returns:
        配置好 CORS、中间件、异常处理和对话路由的 FastAPI 实例。
    """
    settings = get_settings()
    app = FastAPI(
        title="Agent 调度平台 - 运行时",
        description="Agent 对话接口（流式与非流式），对话期间零数据库读取",
        version="0.1.0",
        lifespan=lifespan,
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

    from fastapi import APIRouter

    from src.api.v1 import query

    runtime_router = APIRouter()
    runtime_router.include_router(query.router, prefix="/query", tags=["对话入口"])
    app.include_router(runtime_router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict:
        """健康检查，返回已加载 Agent 数量和 Redis 订阅状态。"""
        context = getattr(app.state, "runtime_context", None)
        redis_task = getattr(app.state, "redis_task", None)
        agents_loaded = context.agent_pool.size() if context else 0
        redis_subscribed = redis_task is not None and not redis_task.done()
        return {
            "status": "ok",
            "agents_loaded": agents_loaded,
            "redis_subscribed": redis_subscribed,
        }

    return app


app = create_runtime_app()
