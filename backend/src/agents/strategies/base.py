"""工具调用策略抽象基类。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseToolStrategy(ABC):
    """工具执行策略抽象基类。

    每种工具协议（MCP、HTTP、BUILTIN）对应一个具体子类。
    新增协议只需实现此接口并注册到 StrategyFactory，
    不需要修改 SingleAgentNode 等调用方。
    """

    @abstractmethod
    async def execute(self, tool_config: dict[str, Any], kwargs: dict[str, Any]) -> str:
        """执行工具调用，返回字符串结果。

        Args:
            tool_config: 工具配置字典，来自 config_snapshot 中的 tools 条目。
                包含 endpoint_url、headers、mcp_tool_name、auth_type 等字段。
            kwargs: 工具调用的实际参数（由 LLM 生成）。

        Returns:
            工具执行结果的字符串表示。

        Raises:
            Exception: 工具调用失败时向上抛出。
        """
