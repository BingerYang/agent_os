"""HTTP 协议工具调用策略：支持 Bearer / API-Key / BasicAuth 认证。"""
from __future__ import annotations

import base64
from typing import Any

from src.agents.strategies.base import BaseToolStrategy


class HTTPToolStrategy(BaseToolStrategy):
    """HTTP POST 工具策略，无状态（可重用实例）。"""

    async def execute(self, tool_config: dict[str, Any], kwargs: dict[str, Any]) -> str:
        """通过 HTTP POST 调用工具端点。

        Args:
            tool_config: 工具配置，需包含 endpoint_url；可选 auth_type 和
                auth_config 字段（支持 BEARER_TOKEN / API_KEY / BASIC_AUTH）。
            kwargs: 工具调用参数，作为 JSON body 发送。

        Returns:
            HTTP 响应体文本。

        Raises:
            httpx.HTTPStatusError: HTTP 响应状态码非 2xx 时抛出。
        """
        import httpx

        endpoint_url: str = tool_config.get("endpoint_url", "")
        auth_type: str = (tool_config.get("auth_type") or "NONE").upper()
        auth_config: dict[str, Any] = tool_config.get("auth_config") or {}

        headers: dict[str, str] = {}
        params: dict[str, str] = {}

        if auth_type == "BEARER_TOKEN":
            headers["Authorization"] = f"Bearer {auth_config.get('token', '')}"
        elif auth_type == "API_KEY":
            if auth_config.get("key_location", "header") == "header":
                headers[auth_config.get("key_name", "X-API-Key")] = auth_config.get("key_value", "")
            else:
                params[auth_config.get("key_name", "api_key")] = auth_config.get("key_value", "")
        elif auth_type == "BASIC_AUTH":
            creds = f"{auth_config.get('username', '')}:{auth_config.get('password', '')}"
            headers["Authorization"] = f"Basic {base64.b64encode(creds.encode()).decode()}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(endpoint_url, json=kwargs, headers=headers, params=params)
            resp.raise_for_status()
            return resp.text
