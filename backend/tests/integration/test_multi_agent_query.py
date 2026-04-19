"""
多 Agent 编排集成测试（T042 - TDD 初始应失败）
测试 MULTI_AGENT Pipeline 的路由和编排流程
"""
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app


async def _create_multi_agent_fixture(client: AsyncClient) -> dict:
    """创建多 Agent 测试所需数据：2 个 SUB Agent + 1 个 MULTI_AGENT Pipeline"""
    # 创建 LLMModel
    resp = await client.post("/api/v1/models", json={
        "name": "multi-test-model",
        "supplier": "openai",
        "model_id": "gpt-4o-mini",
        "api_key": "sk-ZbGrQOLY6DDKEcWlJs_Dnw",
        "category": "chat",
        "endpoint_url": "https://litellm-daily.hszq8.com/v1",
    })
    assert resp.status_code == 200
    llm_id = resp.json()["data"]["id"]

    # 创建 2 个 SUB Agent
    sub_agent_ids = []
    for i in range(2):
        resp = await client.post("/api/v1/agents", json={
            "name": f"子Agent{i+1}",
            "agent_type": "SUB",
            "llm_model_id": llm_id,
            "system_prompt": f"你是子Agent{i+1}，专注处理特定领域查询。",
        })
        assert resp.status_code == 200
        sub_agent_ids.append(resp.json()["data"]["id"])

    # 创建 ORCHESTRATOR Agent（用于路由）
    resp = await client.post("/api/v1/agents", json={
        "name": "编排Agent",
        "agent_type": "ORCHESTRATOR",
        "llm_model_id": llm_id,
        "system_prompt": "你是编排助手，负责将查询路由到合适的子Agent。",
    })
    assert resp.status_code == 200
    orchestrator_id = resp.json()["data"]["id"]

    # 创建 MULTI_AGENT Pipeline
    resp = await client.post("/api/v1/pipelines", json={
        "name": "多Agent测试流水线",
        "pipeline_type": "MULTI_AGENT",
        "primary_agent_id": orchestrator_id,
        "sub_agent_ids": sub_agent_ids,
        "route_confidence_threshold": 0.7,
        "timeout_seconds": 30,
    })
    assert resp.status_code == 200
    pipeline_id = resp.json()["data"]["id"]

    return {
        "pipeline_id": pipeline_id,
        "sub_agent_ids": sub_agent_ids,
        "orchestrator_id": orchestrator_id,
        "llm_id": llm_id,
    }


@pytest.mark.asyncio
async def test_single_sub_agent_routing():
    """单子 Agent 路由（高置信度）：直接转发到置信度最高的子 Agent"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        fixture = await _create_multi_agent_fixture(client)

        resp = await client.post("/api/v1/query", json={
            "query": "你好，请介绍一下自己",
            "pipeline_id": fixture["pipeline_id"],
            "stream": False,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert "answer" in data
        assert data["pipeline_type"] == "MULTI_AGENT"
        assert "session_id" in data
        assert "latency_ms" in data


@pytest.mark.asyncio
async def test_multi_sub_agent_orchestration():
    """多子 Agent 编排：串行调用多个子 Agent 并汇总结果"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        fixture = await _create_multi_agent_fixture(client)

        resp = await client.post("/api/v1/query", json={
            "query": "分析当前市场形势并给出投资建议",
            "pipeline_id": fixture["pipeline_id"],
            "stream": False,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert "answer" in data
        assert len(data["answer"]) > 0


@pytest.mark.asyncio
async def test_sub_agent_timeout_degradation():
    """子 Agent 超时降级：超时时返回降级响应而非报错"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 创建 timeout_seconds=1 的极短超时 Pipeline
        resp = await client.post("/api/v1/models", json={
            "name": "timeout-test-model",
            "supplier": "openai",
            "model_id": "gpt-4o-mini",
            "api_key": "sk-test-key",
            "category": "chat",
        })
        llm_id = resp.json()["data"]["id"]

        resp = await client.post("/api/v1/agents", json={
            "name": "超时子Agent",
            "agent_type": "SUB",
            "llm_model_id": llm_id,
            "system_prompt": "测试超时",
        })
        sub_id = resp.json()["data"]["id"]

        resp = await client.post("/api/v1/agents", json={
            "name": "超时编排Agent",
            "agent_type": "ORCHESTRATOR",
            "llm_model_id": llm_id,
        })
        orch_id = resp.json()["data"]["id"]

        resp = await client.post("/api/v1/pipelines", json={
            "name": "超时测试流水线",
            "pipeline_type": "MULTI_AGENT",
            "primary_agent_id": orch_id,
            "sub_agent_ids": [sub_id],
            "timeout_seconds": 1,  # 极短超时触发降级
        })
        pipeline_id = resp.json()["data"]["id"]

        resp = await client.post("/api/v1/query", json={
            "query": "测试超时降级",
            "pipeline_id": pipeline_id,
            "stream": False,
        })
        assert resp.status_code == 200
        body = resp.json()
        # 超时降级：code=0 返回降级消息，或 code=50801（SubAgentTimeout）
        assert body["code"] in (0, 50801)
