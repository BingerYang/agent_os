"""T039: 单元测试 - HTTPToolStrategy / MCPToolStrategy 覆盖率补充。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.strategies.http_strategy import HTTPToolStrategy
from src.agents.strategies.mcp_strategy import MCPToolStrategy


# ---------- HTTPToolStrategy ----------

@pytest.mark.asyncio
async def test_http_strategy_bearer_token():
    """BEARER_TOKEN 认证时 Authorization 头正确设置。"""
    strategy = HTTPToolStrategy()
    tool_config = {
        "endpoint_url": "http://api.example.com/tool",
        "auth_type": "BEARER_TOKEN",
        "auth_config": {"token": "my-token"},
    }

    mock_resp = MagicMock()
    mock_resp.text = "ok"
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await strategy.execute(tool_config, {"key": "value"})

    assert result == "ok"
    call_kwargs = mock_client.post.call_args
    assert "Authorization" in call_kwargs.kwargs["headers"]
    assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer my-token"


@pytest.mark.asyncio
async def test_http_strategy_api_key_header():
    """API_KEY in header 时 key 正确放入 headers。"""
    strategy = HTTPToolStrategy()
    tool_config = {
        "endpoint_url": "http://api.example.com/tool",
        "auth_type": "API_KEY",
        "auth_config": {"key_location": "header", "key_name": "X-API-Key", "key_value": "secret"},
    }

    mock_resp = MagicMock()
    mock_resp.text = "result"
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await strategy.execute(tool_config, {})

    assert result == "result"
    headers = mock_client.post.call_args.kwargs["headers"]
    assert headers.get("X-API-Key") == "secret"


@pytest.mark.asyncio
async def test_http_strategy_api_key_query():
    """API_KEY in query 时 key 放入 params。"""
    strategy = HTTPToolStrategy()
    tool_config = {
        "endpoint_url": "http://api.example.com/tool",
        "auth_type": "API_KEY",
        "auth_config": {"key_location": "query", "key_name": "api_key", "key_value": "secret"},
    }

    mock_resp = MagicMock()
    mock_resp.text = "result"
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await strategy.execute(tool_config, {})

    params = mock_client.post.call_args.kwargs["params"]
    assert params.get("api_key") == "secret"


@pytest.mark.asyncio
async def test_http_strategy_basic_auth():
    """BASIC_AUTH 时 Authorization 头包含 Basic 前缀。"""
    import base64

    strategy = HTTPToolStrategy()
    tool_config = {
        "endpoint_url": "http://api.example.com/tool",
        "auth_type": "BASIC_AUTH",
        "auth_config": {"username": "user", "password": "pass"},
    }

    mock_resp = MagicMock()
    mock_resp.text = "ok"
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await strategy.execute(tool_config, {})

    headers = mock_client.post.call_args.kwargs["headers"]
    expected = "Basic " + base64.b64encode(b"user:pass").decode()
    assert headers["Authorization"] == expected


@pytest.mark.asyncio
async def test_http_strategy_no_auth():
    """无认证时正常调用。"""
    strategy = HTTPToolStrategy()
    tool_config = {"endpoint_url": "http://api.example.com/tool", "auth_type": "NONE"}

    mock_resp = MagicMock()
    mock_resp.text = "plain"
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await strategy.execute(tool_config, {"a": 1})

    assert result == "plain"


# ---------- MCPToolStrategy ----------

@pytest.mark.asyncio
async def test_mcp_strategy_delegates_to_pool():
    """MCPToolStrategy 将调用代理到 MCPConnectionPool.call_tool。"""
    mock_pool = MagicMock()
    mock_pool.call_tool = AsyncMock(return_value="mcp result")

    strategy = MCPToolStrategy(mcp_pool=mock_pool)
    tool_config = {
        "mcp_server": {"endpoint_url": "http://mcp.server/", "headers": {}},
        "mcp_tool_name": "search",
    }

    result = await strategy.execute(tool_config, {"q": "test"})

    assert result == "mcp result"
    mock_pool.call_tool.assert_called_once_with(
        "http://mcp.server/", "search", {"q": "test"}, {}
    )


@pytest.mark.asyncio
async def test_mcp_strategy_fallback_endpoint():
    """mcp_server 未配置时使用顶层 endpoint_url。"""
    mock_pool = MagicMock()
    mock_pool.call_tool = AsyncMock(return_value="fallback")

    strategy = MCPToolStrategy(mcp_pool=mock_pool)
    tool_config = {
        "endpoint_url": "http://fallback.server/",
        "mcp_tool_name": "tool",
    }

    result = await strategy.execute(tool_config, {})
    assert result == "fallback"
    args = mock_pool.call_tool.call_args[0]
    assert args[0] == "http://fallback.server/"


# ---------- StrategyFactory ----------

def test_strategy_factory_mcp_returns_mcp_strategy():
    """protocol=MCP 返回 MCPToolStrategy。"""
    from src.agents.strategies.factory import StrategyFactory
    from src.agents.strategies.mcp_strategy import MCPToolStrategy

    mock_pool = MagicMock()
    strategy = StrategyFactory.get("MCP", mcp_pool=mock_pool)
    assert isinstance(strategy, MCPToolStrategy)


def test_strategy_factory_http_returns_http_strategy():
    """protocol=HTTP 返回 HTTPToolStrategy。"""
    from src.agents.strategies.factory import StrategyFactory
    from src.agents.strategies.http_strategy import HTTPToolStrategy

    strategy = StrategyFactory.get("HTTP")
    assert isinstance(strategy, HTTPToolStrategy)


def test_strategy_factory_builtin_returns_http_strategy():
    """protocol=BUILTIN 也返回 HTTPToolStrategy。"""
    from src.agents.strategies.factory import StrategyFactory
    from src.agents.strategies.http_strategy import HTTPToolStrategy

    strategy = StrategyFactory.get("BUILTIN")
    assert isinstance(strategy, HTTPToolStrategy)


def test_strategy_factory_mcp_without_pool_raises():
    """MCP 协议不提供 mcp_pool 时抛出 ValueError。"""
    from src.agents.strategies.factory import StrategyFactory

    with pytest.raises(ValueError, match="mcp_pool"):
        StrategyFactory.get("MCP", mcp_pool=None)


def test_strategy_factory_unknown_protocol_raises():
    """未知协议抛出 ValueError。"""
    from src.agents.strategies.factory import StrategyFactory

    with pytest.raises(ValueError, match="不支持的工具协议"):
        StrategyFactory.get("WEBSOCKET")
