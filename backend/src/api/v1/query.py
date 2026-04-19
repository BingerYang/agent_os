"""
查询入口 API（T037）
POST /api/v1/query
支持同步响应（stream=false）和 SSE 流式输出（stream=true）
"""
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from src.core.database import get_db
from src.core.exceptions import PreCheckRejected, PostCheckRejected, ResourceNotFound, BusinessValidationError
from src.core.schemas import ApiResponse
from src.services.query_service import execute_query

router = APIRouter()


class QueryRequest(BaseModel):
    query: str
    pipeline_id: int
    stream: bool = False
    session_id: str | None = None


@router.post("")
async def submit_query(body: QueryRequest, db: AsyncSession = Depends(get_db)) -> Any:
    try:
        if body.stream:
            return await _stream_response(body, db)
        result = await execute_query(db, body.pipeline_id, body.query, body.session_id)
        return ApiResponse.ok(result)
    except PreCheckRejected as e:
        return ApiResponse.error(40301, str(e))
    except PostCheckRejected as e:
        return ApiResponse.error(40302, str(e))
    except ResourceNotFound as e:
        return ApiResponse.error(40401, str(e))
    except BusinessValidationError as e:
        return ApiResponse.error(50001, str(e))


async def _stream_response(body: QueryRequest, db: AsyncSession) -> EventSourceResponse:
    """SSE 流式输出（FR-010）"""

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        try:
            result = await execute_query(db, body.pipeline_id, body.query, body.session_id)
            # 将最终结果以 SSE 格式推送
            import json
            yield {"data": json.dumps({"type": "answer", "content": result["answer"]}, ensure_ascii=False)}
            yield {"data": json.dumps({"type": "done", **result}, ensure_ascii=False)}
        except PreCheckRejected as e:
            import json
            yield {"data": json.dumps({"type": "error", "code": 40301, "message": str(e)}, ensure_ascii=False)}
        except PostCheckRejected as e:
            import json
            yield {"data": json.dumps({"type": "error", "code": 40302, "message": str(e)}, ensure_ascii=False)}
        except Exception as e:
            import json
            yield {"data": json.dumps({"type": "error", "code": 50000, "message": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(event_generator())
