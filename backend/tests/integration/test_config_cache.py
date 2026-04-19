"""
Config Cache 集成测试（T060）

按 TDD 编写：当前运行时应保持失败，不实现业务代码。
"""
from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.database import AsyncSessionLocal
from src.main import app


def _get_config_cache_class():
    try:
        from src.services.config_cache import ConfigCache
    except ModuleNotFoundError:
        ConfigCache = None

    assert ConfigCache is not None, "Expected src.services.config_cache.ConfigCache to exist for T060"
    return ConfigCache


def _extract_ids(items: list[Any]) -> list[int]:
    ids: list[int] = []
    for item in items:
        if isinstance(item, dict):
            ids.append(item["id"])
        else:
            ids.append(item.id)
    return ids


async def _create_tool(client: AsyncClient, *, name: str) -> int:
    response = await client.post(
        "/api/v1/tools",
        json={
            "name": name,
            "display_name": f"{name}-display",
            "description": f"{name} description",
            "protocol": "BUILTIN",
            "input_schema": {"type": "object"},
            "tags": ["config-cache", "integration"],
            "version": "v1.0.0",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    return body["data"]["id"]


async def _create_skill(client: AsyncClient, *, name: str, tool_id: int) -> int:
    response = await client.post(
        "/api/v1/skills",
        json={
            "name": name,
            "description": f"{name} description",
            "trigger_condition": "config cache integration",
            "tags": ["config-cache", "integration"],
            "version": "v1.0.0",
            "tool_ids": [tool_id],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    return body["data"]["id"]


async def _create_agent(client: AsyncClient, *, name: str) -> int:
    response = await client.post(
        "/api/v1/agents",
        json={
            "name": name,
            "description": f"{name} description",
            "agent_type": "SINGLE",
            "source_platform": "local",
            "system_prompt": "You are a cache validation agent.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    return body["data"]["id"]


async def _seed_config_entities(client: AsyncClient) -> dict[str, int]:
    tool_id = await _create_tool(client, name="config_cache_tool")
    skill_id = await _create_skill(client, name="config_cache_skill", tool_id=tool_id)
    agent_id = await _create_agent(client, name="config_cache_agent")
    return {"tool_id": tool_id, "skill_id": skill_id, "agent_id": agent_id}


@pytest.mark.asyncio
async def test_load_snapshot():
    """load_snapshot 应从数据库装载启用配置。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _seed_config_entities(client)

    ConfigCache = _get_config_cache_class()
    cache = ConfigCache()

    async with AsyncSessionLocal() as db:
        await cache.load_snapshot(db)

    enabled_tools = cache.get_enabled_tools()
    assert enabled_tools


@pytest.mark.asyncio
async def test_apply_event_updates_cache():
    """apply_event 应根据配置事件实时移除已禁用工具。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ids = await _seed_config_entities(client)

    ConfigCache = _get_config_cache_class()
    cache = ConfigCache()

    async with AsyncSessionLocal() as db:
        await cache.load_snapshot(db)

    cache.apply_event({"entity_type": "tool", "entity_id": ids["tool_id"], "action": "disable"})

    assert ids["tool_id"] not in _extract_ids(cache.get_enabled_tools())


@pytest.mark.asyncio
async def test_cache_available_when_db_unreachable():
    """完成快照后，即使没有可用 db session，也应继续返回内存缓存。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _seed_config_entities(client)

    ConfigCache = _get_config_cache_class()
    cache = ConfigCache()

    async with AsyncSessionLocal() as db:
        await cache.load_snapshot(db)
        snapshot_tool_ids = _extract_ids(cache.get_enabled_tools())

    enabled_tools = cache.get_enabled_tools()
    assert _extract_ids(enabled_tools) == snapshot_tool_ids


@pytest.mark.asyncio
async def test_cache_reload_after_restart():
    """新实例在重新 load_snapshot 后应恢复缓存内容。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _seed_config_entities(client)

    ConfigCache = _get_config_cache_class()
    first_cache = ConfigCache()

    async with AsyncSessionLocal() as db:
        await first_cache.load_snapshot(db)
        expected_tool_ids = _extract_ids(first_cache.get_enabled_tools())

    restarted_cache = ConfigCache()
    async with AsyncSessionLocal() as db:
        await restarted_cache.load_snapshot(db)

    assert _extract_ids(restarted_cache.get_enabled_tools()) == expected_tool_ids
