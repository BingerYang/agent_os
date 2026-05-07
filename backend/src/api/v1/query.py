"""查询入口 API（T029）
POST /api/v1/query
支持同步响应（stream=false）和 SSE 流式输出（stream=true）。
对话路径零数据库读取，所有数据来自 RuntimeContext 内存池。
"""
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.core.exceptions import BusinessValidationError, PostCheckRejected, PreCheckRejected, ResourceNotFound
from src.core.schemas import ApiResponse
from src.services.query_service import execute_query, execute_stream_query

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    pipeline_id: str
    stream: bool = False
    session_id: str | None = None


def get_runtime_context(request: Request) -> Any:
    """从 app.state 获取 RuntimeContext（由 main_runtime.py lifespan 注入）。"""
    ctx = getattr(request.app.state, "runtime_context", None)
    if ctx is None:
        raise BusinessValidationError("运行时上下文未初始化，请确认使用运行时服务启动")
    return ctx


@router.post("")
async def submit_query(body: QueryRequest, request: Request) -> Any:
    context = get_runtime_context(request)
    try:
        if body.stream:
            return await _stream_response(body, context)
        result = await execute_query(context, body.pipeline_id, body.query, body.session_id)
        return ApiResponse.ok(result)
    except PreCheckRejected as e:
        return ApiResponse.error(40301, str(e))
    except PostCheckRejected as e:
        return ApiResponse.error(40302, str(e))
    except ResourceNotFound as e:
        return ApiResponse.error(40401, str(e))
    except BusinessValidationError as e:
        return ApiResponse.error(50001, str(e))


async def _stream_response(body: QueryRequest, context: Any) -> EventSourceResponse:
    """SSE 真实流式输出。"""

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        try:
            async for event in execute_stream_query(
                context, body.pipeline_id, body.query, body.session_id
            ):
                yield {"data": json.dumps(event, ensure_ascii=False)}
        except Exception as e:
            yield {
                "data": json.dumps(
                    {"type": "error", "code": 50000, "message": str(e)},
                    ensure_ascii=False,
                )
            }

    return EventSourceResponse(event_generator())
