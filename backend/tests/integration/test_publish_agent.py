"""T015: TDD 测试 - PATCH /agents/{id}/publish 端点。"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import AsyncSessionLocal


async def _create_test_agent(db: AsyncSession, with_llm: bool = True) -> int:
    """创建测试用 Agent，可选是否附带 LLM 配置。"""
    from src.models.agent import Agent, AgentType
    from src.models.llm_model import LLMModel

    llm_id = None
    if with_llm:
        llm = LLMModel(
            name="test-llm",
            model_id="gpt-4o-test",
            supplier="openai",
            category="chat",
            api_key="test-key",
        )
        db.add(llm)
        await db.flush()
        llm_id = llm.id

    agent = Agent(
        name="test-agent",
        agent_type=AgentType.SINGLE,
        llm_model_id=llm_id,
        system_prompt="你是测试助手",
        temperature=0.7,
        max_tokens=1024,
    )
    db.add(agent)
    await db.flush()
    await db.commit()
    return agent.id


@pytest.mark.asyncio
async def test_publish_agent_creates_record():
    """成功发布创建 AgentPublish 记录，版本从 1 开始递增。"""
    from src.main import app
    from src.models.agent_publish import AgentPublish
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        agent_id = await _create_test_agent(db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(f"/api/v1/agents/{agent_id}/publish")

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["version"] == 1
    assert data["data"]["agent_id"] == agent_id
    assert "publish_id" in data["data"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AgentPublish).where(AgentPublish.agent_id == agent_id)
        )
        pub = result.scalar_one_or_none()
        assert pub is not None
        assert pub.is_active is True
        assert pub.version == 1


@pytest.mark.asyncio
async def test_publish_agent_version_increments():
    """连续发布版本号递增，旧记录 is_active 变为 False。"""
    from src.main import app
    from src.models.agent_publish import AgentPublish
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        agent_id = await _create_test_agent(db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.patch(f"/api/v1/agents/{agent_id}/publish")
        resp2 = await client.patch(f"/api/v1/agents/{agent_id}/publish")

    assert resp2.json()["data"]["version"] == 2

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AgentPublish).where(AgentPublish.agent_id == agent_id).order_by(AgentPublish.version)
        )
        pubs = result.scalars().all()
        assert len(pubs) == 2
        assert pubs[0].is_active is False  # 旧版本
        assert pubs[1].is_active is True   # 新版本


@pytest.mark.asyncio
async def test_publish_agent_not_found():
    """Agent 不存在返回 404。"""
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch("/api/v1/agents/999999/publish")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_publish_agent_no_llm_returns_error():
    """Agent 未配置 LLM 模型时返回错误（code != 0 或 400）。"""
    from src.main import app

    async with AsyncSessionLocal() as db:
        agent_id = await _create_test_agent(db, with_llm=False)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(f"/api/v1/agents/{agent_id}/publish")

    assert resp.status_code in (400, 422) or resp.json().get("code") != 0


@pytest.mark.asyncio
async def test_publish_agent_redis_failure_still_succeeds():
    """Redis 不可用时 redis_notified=false，但操作整体仍成功（code=0）。"""
    from unittest.mock import patch, AsyncMock
    from src.main import app

    async with AsyncSessionLocal() as db:
        agent_id = await _create_test_agent(db)

    with patch(
        "src.services.publish_service._push_redis_event",
        new=AsyncMock(return_value=False),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.patch(f"/api/v1/agents/{agent_id}/publish")

    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["redis_notified"] is False
