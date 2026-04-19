"""
Marketplace 契约测试（T051）

按 TDD 编写：当前运行时应保持失败，不实现业务代码。
"""
from __future__ import annotations

from typing import Any

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


MARKETPLACE_ITEM_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "item_type", "enabled"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "item_type": {"type": "string", "enum": ["tool", "skill", "agent"]},
        "enabled": {"type": "boolean"},
    },
    "additionalProperties": True,
}

API_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["code", "message", "data", "timestamp"],
    "properties": {
        "code": {"type": "integer"},
        "message": {"type": "string"},
        "data": {},
        "timestamp": {"type": "string"},
    },
    "additionalProperties": False,
}

MARKETPLACE_LIST_RESPONSE_SCHEMA = {
    **API_RESPONSE_SCHEMA,
    "properties": {
        **API_RESPONSE_SCHEMA["properties"],
        "data": {
            "type": "object",
            "required": ["items", "total"],
            "properties": {
                "items": {"type": "array", "items": MARKETPLACE_ITEM_SCHEMA},
                "total": {"type": "integer"},
            },
            "additionalProperties": False,
        },
    },
}

INSTALL_RESPONSE_SCHEMA = {
    **API_RESPONSE_SCHEMA,
    "properties": {
        **API_RESPONSE_SCHEMA["properties"],
        "data": MARKETPLACE_ITEM_SCHEMA,
    },
}


def _assert_matches_schema(instance: Any, schema: dict[str, Any], path: str = "$") -> None:
    schema_type = schema.get("type")
    if schema_type == "object":
        assert isinstance(instance, dict), f"{path} 应为 object"
        required = schema.get("required", [])
        for key in required:
            assert key in instance, f"{path} 缺少必填字段 {key}"

        properties = schema.get("properties", {})
        additional_properties = schema.get("additionalProperties", True)
        if additional_properties is False:
            assert set(instance.keys()) <= set(properties.keys()), f"{path} 存在未声明字段 {set(instance.keys()) - set(properties.keys())}"

        for key, value in instance.items():
            if key in properties:
                _assert_matches_schema(value, properties[key], f"{path}.{key}")
        return

    if schema_type == "array":
        assert isinstance(instance, list), f"{path} 应为 array"
        item_schema = schema.get("items", {})
        for index, item in enumerate(instance):
            _assert_matches_schema(item, item_schema, f"{path}[{index}]")
        return

    if schema_type == "string":
        assert isinstance(instance, str), f"{path} 应为 string"
    elif schema_type == "integer":
        assert isinstance(instance, int) and not isinstance(instance, bool), f"{path} 应为 integer"
    elif schema_type == "boolean":
        assert isinstance(instance, bool), f"{path} 应为 boolean"

    enum_values = schema.get("enum")
    if enum_values is not None:
        assert instance in enum_values, f"{path} 不在枚举值 {enum_values} 中"


async def _create_tool(client: AsyncClient, *, name: str) -> int:
    response = await client.post(
        "/api/v1/tools",
        json={
            "name": name,
            "display_name": f"{name}-display",
            "description": f"{name} description",
            "protocol": "BUILTIN",
            "input_schema": {"type": "object"},
            "tags": ["marketplace", "contract"],
            "version": "v1.0.0",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


class _FakeConnectivityClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def head(self, url: str, headers: dict[str, str] | None = None):
        return httpx.Response(200)

    async def get(self, url: str, headers: dict[str, str] | None = None):
        return httpx.Response(200)

    async def post(self, url: str, headers: dict[str, str] | None = None, json: dict[str, Any] | None = None):
        return httpx.Response(200, json={"ok": True})


@pytest.mark.asyncio
async def test_marketplace_list_response_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _create_tool(client, name="marketplace_contract_list_tool")

        response = await client.get("/api/v1/marketplace")
        assert response.status_code == 200
        _assert_matches_schema(response.json(), MARKETPLACE_LIST_RESPONSE_SCHEMA)


@pytest.mark.asyncio
async def test_marketplace_install_response_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tool_id = await _create_tool(client, name="marketplace_contract_install_tool")

        response = await client.post(f"/api/v1/marketplace/tool/{tool_id}/install")
        assert response.status_code == 200
        _assert_matches_schema(response.json(), INSTALL_RESPONSE_SCHEMA)


@pytest.mark.asyncio
async def test_marketplace_uninstall_response_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tool_id = await _create_tool(client, name="marketplace_contract_uninstall_tool")

        response = await client.delete(f"/api/v1/marketplace/tool/{tool_id}/install")
        assert response.status_code == 200
        _assert_matches_schema(response.json(), INSTALL_RESPONSE_SCHEMA)


@pytest.mark.asyncio
async def test_register_agent_request_schema_requires_access_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeConnectivityClient)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/marketplace/agents",
            json={
                "name": "marketplace_contract_agent",
                "access_url": "https://third-party-agent.example.com",
            },
        )

        assert response.status_code == 422
