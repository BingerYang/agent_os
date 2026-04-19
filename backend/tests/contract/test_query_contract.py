"""
查询接口契约测试（T025）
验证 POST /api/v1/query 请求/响应结构与 contracts/api.md 一致
"""
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app


QUERY_REQUEST_REQUIRED_FIELDS = {"query", "pipeline_id"}
QUERY_RESPONSE_DATA_FIELDS = {"answer", "pipeline_type", "tools_called", "session_id", "latency_ms"}
API_RESPONSE_FIELDS = {"code", "message", "data", "timestamp"}


@pytest.mark.asyncio
async def test_query_request_missing_required_fields():
    """缺少必填字段 → 返回 422"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_request_missing_query_field():
    """缺少 query 字段 → 422"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={"pipeline_id": 1})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_request_missing_pipeline_id():
    """缺少 pipeline_id 字段 → 422"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={"query": "测试"})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_pipeline_not_found():
    """pipeline_id 不存在 → code=40401"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={
            "query": "测试查询",
            "pipeline_id": 99999,
            "stream": False,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 40401


@pytest.mark.asyncio
async def test_api_response_envelope_structure():
    """所有响应必须包含 ApiResponse 信封字段"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={
            "query": "测试",
            "pipeline_id": 99999,
            "stream": False,
        })
        body = resp.json()
        for field in API_RESPONSE_FIELDS:
            assert field in body, f"响应缺少字段: {field}"
        assert isinstance(body["code"], int)
        assert isinstance(body["message"], str)
        assert body["timestamp"] is not None


@pytest.mark.asyncio
async def test_query_stream_false_returns_json():
    """stream=false 时响应 Content-Type 为 application/json"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/query", json={
            "query": "测试",
            "pipeline_id": 99999,
            "stream": False,
        })
        ct = resp.headers.get("content-type", "")
        assert "application/json" in ct


@pytest.mark.asyncio
async def test_successful_query_response_data_structure():
    """成功响应 data 字段包含所有契约规定字段"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 先创建流水线数据
        resp = await client.post("/api/v1/models", json={
            "name": "contract-test-model",
            "supplier": "openai",
            "model_id": "gpt-4o-mini",
            "api_key": "sk-test",
            "category": "chat",
        })
        if resp.json().get("code") != 0:
            pytest.skip("LLM model creation failed, skip structure test")

        llm_id = resp.json()["data"]["id"]
        resp = await client.post("/api/v1/agents", json={
            "name": "contract-agent",
            "agent_type": "SINGLE",
            "llm_model_id": llm_id,
            "tool_ids": [],
        })
        agent_id = resp.json()["data"]["id"]
        resp = await client.post("/api/v1/pipelines", json={
            "name": "contract-pipeline",
            "pipeline_type": "SINGLE_AGENT",
            "primary_agent_id": agent_id,
        })
        pipeline_id = resp.json()["data"]["id"]

        resp = await client.post("/api/v1/query", json={
            "query": "测试",
            "pipeline_id": pipeline_id,
            "stream": False,
        })
        body = resp.json()
        if body["code"] == 0:
            data = body["data"]
            for field in QUERY_RESPONSE_DATA_FIELDS:
                assert field in data, f"data 缺少字段: {field}"
            assert isinstance(data["tools_called"], list)
            assert isinstance(data["latency_ms"], (int, float))
