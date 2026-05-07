"""T044: 查询接口契约测试 - 验证 POST /api/v1/query 请求/响应结构。"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.agents.pool.agent_pool import AgentPool
from src.agents.pool.mcp_pool import MCPConnectionPool
from src.agents.pool.skill_pool import SkillPool
from src.agents.pool.tool_pool import ToolPool
from src.runtime.context import RuntimeContext

QUERY_RESPONSE_DATA_FIELDS = {"answer", "pipeline_type", "tools_called", "session_id", "latency_ms"}
API_RESPONSE_FIELDS = {"code", "message", "data", "timestamp"}


def _make_empty_context() -> RuntimeContext:
    """空 RuntimeContext（无任何流水线）。"""
    return RuntimeContext(
        agent_pool=AgentPool(),
        tool_pool=ToolPool(),
        skill_pool=SkillPool(),
        mcp_pool=MCPConnectionPool(),
        pipeline_cache={},
        detection_cache={},
    )


@pytest.fixture
def runtime_app():
    """创建 runtime app 并直接注入空 RuntimeContext（ASGITransport 不触发 lifespan）。"""
    from src.main_runtime import create_runtime_app
    app = create_runtime_app()
    app.state.runtime_context = _make_empty_context()
    return app


@pytest.mark.asyncio
async def test_query_request_missing_required_fields(runtime_app):
    """缺少必填字段 → 返回 422。"""
    async with AsyncClient(transport=ASGITransport(app=runtime_app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_request_missing_query_field(runtime_app):
    """缺少 query 字段 → 422。"""
    async with AsyncClient(transport=ASGITransport(app=runtime_app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={"pipeline_id": "pl-001"})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_request_missing_pipeline_id(runtime_app):
    """缺少 pipeline_id 字段 → 422。"""
    async with AsyncClient(transport=ASGITransport(app=runtime_app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={"query": "测试"})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_pipeline_not_found(runtime_app):
    """pipeline_id 不存在 → code=40401。"""
    async with AsyncClient(transport=ASGITransport(app=runtime_app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={
            "query": "测试查询",
            "pipeline_id": "nonexistent-uid",
            "stream": False,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 40401


@pytest.mark.asyncio
async def test_api_response_envelope_structure(runtime_app):
    """所有响应必须包含 ApiResponse 信封字段。"""
    async with AsyncClient(transport=ASGITransport(app=runtime_app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={
            "query": "测试",
            "pipeline_id": "nonexistent-uid",
            "stream": False,
        })
        body = resp.json()
        for field in API_RESPONSE_FIELDS:
            assert field in body, f"响应缺少字段: {field}"
        assert isinstance(body["code"], int)
        assert isinstance(body["message"], str)
        assert body["timestamp"] is not None


@pytest.mark.asyncio
async def test_query_stream_false_returns_json(runtime_app):
    """stream=false 时响应 Content-Type 为 application/json。"""
    async with AsyncClient(transport=ASGITransport(app=runtime_app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={
            "query": "测试",
            "pipeline_id": "nonexistent-uid",
            "stream": False,
        })
        assert "application/json" in resp.headers.get("content-type", "")
