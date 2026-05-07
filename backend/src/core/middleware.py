import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.core.exceptions import AgentOSError
from src.core.schemas import ApiResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.time()
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000
        logger.info(f"{request.method} {request.url.path} {response.status_code} {elapsed:.1f}ms")
        return response


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AgentOSError)
    async def handle_platform_error(request: Request, exc: AgentOSError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse.error(exc.error_code, exc.message).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def handle_generic_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"未处理的异常: {exc}")
        return JSONResponse(
            status_code=500,
            content=ApiResponse.error(50001, "服务器内部错误").model_dump(mode="json"),
        )
