"""
Marketplace 集成测试（T050）

按 TDD 编写：当前运行时应保持失败，不实现业务代码。
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


async def _create_tool(client: AsyncClient, *, name: str, enabled: bool) -> int:
    response = await client.post(
        "/api/v1/tools",
        json={
            "name": name,
            "display_name": f"{name}-display",
            "description": f"{name} description",
            "protocol": "BUILTIN",
            "input_schema": {"type": "object"},
            "tags": ["marketplace", "integration"],
            "version": "v1.0.0",
        },
    )
    assert response.status_code == 200
    tool_id = response.json()["data"]["id"]

    if not enabled:
        toggle_response = await client.patch(f"/api/v1/tools/{tool_id}/toggle", json={"enabled": False})
        assert toggle_response.status_code == 200
        assert toggle_response.json()["data"]["enabled"] is False

    return tool_id


async def _create_skill(client: AsyncClient, *, name: str, enabled: bool) -> int:
    response = await client.post(
        "/api/v1/skills",
        json={
            "name": name,
            "description": f"{name} description",
            "trigger_condition": "marketplace install",
            "tags": ["marketplace", "integration"],
            "version": "v1.0.0",
        },
    )
    assert response.status_code == 200
    skill_id = response.json()["data"]["id"]

    if not enabled:
        toggle_response = await client.patch(f"/api/v1/skills/{skill_id}/toggle", json={"enabled": False})
        assert toggle_response.status_code == 200
        assert toggle_response.json()["data"]["enabled"] is False

    return skill_id


@pytest.mark.asyncio
async def test_install_tool():
    """POST /api/v1/marketplace/tool/{id}/install → 返回 Tool 风格资源，且 enabled=True。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tool_name = "marketplace_install_tool"
        tool_id = await _create_tool(client, name=tool_name, enabled=False)

        response = await client.post(f"/api/v1/marketplace/tool/{tool_id}/install")
        assert response.status_code == 200

        body = response.json()
        assert body["code"] == 0
        assert body["data"]["id"] == tool_id
        assert body["data"]["name"] == tool_name
        assert body["data"]["display_name"] == f"{tool_name}-display"
        assert body["data"]["protocol"] == "BUILTIN"
        assert body["data"]["enabled"] is True

        tool_response = await client.get(f"/api/v1/tools/{tool_id}")
        assert tool_response.status_code == 200
        assert tool_response.json()["data"]["enabled"] is True


@pytest.mark.asyncio
async def test_uninstall_tool():
    """DELETE /api/v1/marketplace/tool/{id}/install → 返回 Tool 风格资源，且 enabled=False。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tool_name = "marketplace_uninstall_tool"
        tool_id = await _create_tool(client, name=tool_name, enabled=True)

        response = await client.delete(f"/api/v1/marketplace/tool/{tool_id}/install")
        assert response.status_code == 200

        body = response.json()
        assert body["code"] == 0
        assert body["data"]["id"] == tool_id
        assert body["data"]["name"] == tool_name
        assert body["data"]["display_name"] == f"{tool_name}-display"
        assert body["data"]["protocol"] == "BUILTIN"
        assert body["data"]["enabled"] is False

        tool_response = await client.get(f"/api/v1/tools/{tool_id}")
        assert tool_response.status_code == 200
        assert tool_response.json()["data"]["enabled"] is False


@pytest.mark.asyncio
async def test_install_skill():
    """POST /api/v1/marketplace/skill/{id}/install → 返回 Skill 风格资源，且 enabled=True。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        skill_name = "marketplace_install_skill"
        skill_id = await _create_skill(client, name=skill_name, enabled=False)

        response = await client.post(f"/api/v1/marketplace/skill/{skill_id}/install")
        assert response.status_code == 200

        body = response.json()
        assert body["code"] == 0
        assert body["data"]["id"] == skill_id
        assert body["data"]["name"] == skill_name
        assert body["data"]["trigger_condition"] == "marketplace install"
        assert body["data"]["enabled"] is True

        skill_response = await client.get(f"/api/v1/skills/{skill_id}")
        assert skill_response.status_code == 200
        assert skill_response.json()["data"]["enabled"] is True


@pytest.mark.asyncio
async def test_register_third_party_agent_connectivity_fail():
    """POST /api/v1/marketplace/agents，access_url 不可达时应返回 400。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/marketplace/agents",
            json={
                "name": "marketplace_unreachable_agent",
                "access_url": "http://127.0.0.1:9/unreachable",
                "access_token": "Bearer demo-token",
            },
        )

        assert response.status_code == 400
        body = response.json()
        assert body["code"] != 0
