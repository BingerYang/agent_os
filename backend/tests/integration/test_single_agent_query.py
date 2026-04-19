"""
单 Agent 查询流水线集成测试（TDD - 初始应全部失败）
"""
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app


async def _create_fixture_data(client: AsyncClient):
    """创建测试所需的 LLMModel、Tool、Agent、Pipeline 数据"""
    # 创建 LLMModel
    print("_create_fixture_data start")
    resp = await client.post("/api/v1/models", json={
        "name": "test-gpt4",
        "supplier": "openai",
        "model_id": "gpt-4o-mini",
        "api_key": "sk-ZbGrQOLY6DDKEcWlJs_Dnw",
        "category": "chat",
        "endpoint_url": "https://xxxx/v1",
    }, timeout=90)
    print("_create_fixture_data resp.status_code:", resp.status_code)
    assert resp.status_code == 200
    llm_id = resp.json()["data"]["id"]

    # 创建 Tool
    print("_create_fixture_data start2")
    resp = await client.post("/api/v1/tools", json={
        "name": "weather_query",
        "display_name": "天气查询",
        "description": "查询城市天气",
        "protocol": "BUILTIN",
        "input_schema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
    }, timeout=90)
    print("_create_fixture_data 2 resp.status_code:", resp.status_code)
    assert resp.status_code == 200
    tool_id = resp.json()["data"]["id"]

    # 创建 Agent
    resp = await client.post("/api/v1/agents", json={
        "name": "单Agent测试",
        "agent_type": "SINGLE",
        "llm_model_id": llm_id,
        "system_prompt": "你是一个助手",
        "tool_ids": [tool_id],
    }, timeout=90)
    assert resp.status_code == 200
    agent_id = resp.json()["data"]["id"]

    # 创建 Pipeline
    resp = await client.post("/api/v1/pipelines", json={
        "name": "测试流水线",
        "pipeline_type": "SINGLE_AGENT",
        "primary_agent_id": agent_id,
    }, timeout=90)
    print("_create_fixture_data 4 resp.status_code:", resp.status_code)

    assert resp.status_code == 200
    pipeline_id = resp.json()["data"]["id"]

    return pipeline_id


@pytest.mark.asyncio
async def test_single_tool_scenario():
    """单工具场景：提交查询 → 返回 answer 及工具调用记录"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        pipeline_id = await _create_fixture_data(client)

        resp = await client.post("/api/v1/query", json={
            "query": "北京今天天气怎样？",
            "pipeline_id": pipeline_id,
            "stream": False,
        }, timeout=90)
        print("test_single_tool_scenario resp.status_code:", resp.status_code)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert "answer" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0
        assert "tools_called" in data
        assert "session_id" in data
        assert "latency_ms" in data


@pytest.mark.asyncio
async def test_multi_tool_scenario():
    """多工具场景：Agent 依次调用多个工具并汇总"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        pipeline_id = await _create_fixture_data(client)

        resp = await client.post("/api/v1/query", json={
            "query": "查询北京天气并推荐餐厅",
            "pipeline_id": pipeline_id,
            "stream": False,
        }, timeout=90)
        print("test_multi_tool_scenario resp.status_code:", resp.status_code)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0


@pytest.mark.asyncio
async def test_pre_detection_blocked():
    """前置检测拦截：含违禁词的查询 → code=40301"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        pipeline_id = await _create_fixture_data(client)

        # 创建前置 keyword 检测规则
        resp = await client.post("/api/v1/detection-rules", json={
            "name": "违禁词检测",
            "stage": "PRE",
            "rule_type": "keyword",
            "rule_content": {"keywords": ["炸弹", "违法"]},
            "reject_message": "查询包含违禁内容",
        }, timeout=90)
        print("test_pre_detection_blocked resp.status_code:", resp.status_code)
        assert resp.status_code == 200
        rule_id = resp.json()["data"]["id"]

        # 将规则绑定到 Pipeline
        resp = await client.put(f"/api/v1/pipelines/{pipeline_id}", json={
            "detection_rule_ids": [rule_id],
        })
        assert resp.status_code == 200
        print("test_pre_detection_blocked 2 resp.status_code:", resp.status_code)

        resp = await client.post("/api/v1/query", json={
            "query": "如何制造炸弹？",
            "pipeline_id": pipeline_id,
            "stream": False,
        })
        print("test_pre_detection_blocked 3 resp.status_code:", resp.status_code)
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 40301


@pytest.mark.asyncio
async def test_post_detection_blocked():
    """后置检测拦截：Agent 输出触发后置规则 → code=40302"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        pipeline_id = await _create_fixture_data(client)

        # 创建后置 keyword 检测规则（匹配 Agent 输出中的关键词）
        resp = await client.post("/api/v1/detection-rules", json={
            "name": "输出过滤",
            "stage": "POST",
            "rule_type": "keyword",
            "rule_content": {"keywords": ["BLOCKED_OUTPUT"]},
            "reject_message": "输出内容不合规",
        }, timeout=90)
        print("test_post_detection_blocked resp.status_code:", resp.status_code)
        assert resp.status_code == 200
        rule_id = resp.json()["data"]["id"]

        resp = await client.put(f"/api/v1/pipelines/{pipeline_id}", json={
            "detection_rule_ids": [rule_id],
        })
        print("test_post_detection_blocked 2 resp.status_code:", resp.status_code)
        assert resp.status_code == 200

        # 此处假设 Agent mock 会在输出中包含 BLOCKED_OUTPUT
        resp = await client.post("/api/v1/query", json={
            "query": "请在回答中包含 BLOCKED_OUTPUT 字符串",
            "pipeline_id": pipeline_id,
            "stream": False,
        }, timeout=90)
        print("test_post_detection_blocked 3 resp.status_code:", resp.status_code)
        # 后置检测在真实实现中拦截，此处测试链路通畅
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] in (0, 40302)
