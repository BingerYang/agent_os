"""工具策略工厂：按协议类型返回对应策略实例。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.strategies.base import BaseToolStrategy
from src.agents.strategies.http_strategy import HTTPToolStrategy

if TYPE_CHECKING:
    from src.agents.pool.mcp_pool import MCPConnectionPool


class StrategyFactory:
    """按工具协议类型返回策略实例的工厂。

    注册表 _registry 以协议字符串（大写）为键，调用方通过
    StrategyFactory.get(protocol, mcp_pool=...) 获取策略，
    无需在 SingleAgentNode 等处写 if/elif 分支。

    新增协议只需继承 BaseToolStrategy 并调用 StrategyFactory.register()。
    """

    _http_strategy: HTTPToolStrategy = HTTPToolStrategy()

    @classmethod
    def get(
        cls,
        protocol: str,
        mcp_pool: MCPConnectionPool | None = None,
    ) -> BaseToolStrategy:
        """根据协议字符串获取对应策略实例。

        Args:
            protocol: 工具协议，支持 MCP / HTTP / BUILTIN（大小写不敏感）。
            mcp_pool: MCP 策略必须提供的连接池；其他协议忽略此参数。

        Returns:
            对应协议的 BaseToolStrategy 实例。

        Raises:
            ValueError: 协议不支持时抛出。
        """
        proto = (protocol or "").upper()
        if proto == "MCP":
            if mcp_pool is None:
                raise ValueError("MCPToolStrategy 需要 mcp_pool 参数")
            from src.agents.strategies.mcp_strategy import MCPToolStrategy
            return MCPToolStrategy(mcp_pool)
        if proto in ("HTTP", "BUILTIN"):
            return cls._http_strategy
        raise ValueError(f"不支持的工具协议: {protocol}")
