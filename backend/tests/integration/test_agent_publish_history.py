"""T016: TDD 测试 - GET /agents/{id}/publishes 发布历史端点。"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from src.core.database import AsyncSessionLocal


async def _setup_published_agent() -> tuple[int, list[int]]:
    """创建并发布两次的测试 Agent，返回 (agent_id, [pub_id_1, pub_id_2])。"""
    from src.models.agent import Agent, AgentType
    from src.models.llm_model import LLMModel
    from src.services.publish_service import publish_agent

    async with AsyncSessionLocal() as db:
        llm = LLMModel(
            name="hist-llm",
            model_id="gpt-4o-hist",
            supplier="openai",
            category="chat",
            api_key="test-key",
        )
        db.add(llm)
        await db.flush()

        agent = Agent(
            name="history-agent",
            agent_type=AgentType.SINGLE,
            llm_model_id=llm.id,
            system_prompt="历史测试",
        )
        db.add(agent)
        await db.flush()
        await db.commit()
        agent_id = agent.id

    async with AsyncSessionLocal() as db:
        r1 = await publish_agent(db, agent_id)
    async with AsyncSessionLocal() as db:
        r2 = await publish_agent(db, agent_id)

    return agent_id, [r1.publish_id, r2.publish_id]


@pytest.mark.asyncio
async def test_get_publish_history_returns_list():
    """GET /agents/{id}/publishes 返回发布历史列表，按版本降序。"""
    from src.main import app

    agent_id, pub_ids = await _setup_published_agent()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/agents/{agent_id}/publishes")

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    items = data["data"]["items"]
    assert len(items) == 2
    # 按版本降序
    assert items[0]["version"] > items[1]["version"]


@pytest.mark.asyncio
async def test_get_publish_history_pagination():
    """GET /agents/{id}/publishes 支持 page/page_size 分页。"""
    from src.main import app

    agent_id, _ = await _setup_published_agent()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/agents/{agent_id}/publishes",
            params={"page": 1, "page_size": 1},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["total"] == 2
    assert len(data["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_get_publish_history_empty():
    """未发布过的 Agent 返回空列表。"""
    from src.main import app
    from src.models.agent import Agent, AgentType

    async with AsyncSessionLocal() as db:
        agent = Agent(name="no-publish-agent", agent_type=AgentType.SINGLE)
        db.add(agent)
        await db.flush()
        await db.commit()
        agent_id = agent.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/agents/{agent_id}/publishes")

    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0
