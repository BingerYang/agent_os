from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.database import init_db
from src.core.middleware import RequestLoggingMiddleware, register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Agent 调度平台",
        description="可配置可扩展智能体编排系统 API",
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

    from src.api.v1.router import api_router
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
