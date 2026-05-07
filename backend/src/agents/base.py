"""Agent 运行时抽象基类与共享数据模型。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.agents.pool.agent_pool import AgentPool
    from src.agents.pool.mcp_pool import MCPConnectionPool
    from src.agents.pool.tool_pool import ToolPool
    from src.runtime.context import PipelineCacheEntry


@dataclass
class AgentContext:
    """单次对话的执行上下文，注入给 BaseNode。

    Attributes:
        query: 用户输入的自然语言查询。
        session_id: 本次会话 ID。
        pipeline_config: 当前流水线的缓存配置。
        agent_pool: 运行时 Agent 池引用。
        tool_pool: 运行时工具池引用。
        mcp_pool: MCP 长连接池引用。
    """

    query: str
    session_id: str
    pipeline_config: PipelineCacheEntry
    agent_pool: AgentPool
    tool_pool: ToolPool
    mcp_pool: MCPConnectionPool


@dataclass
class AgentResult:
    """Agent 执行结果。

    Attributes:
        answer: 最终自然语言回答。
        tools_called: 本次调用中使用的工具名称列表（去重）。
        session_id: 会话 ID。
        latency_ms: 执行耗时（毫秒）。
        pipeline_type: 流水线类型（SINGLE_AGENT / MULTI_AGENT）。
        sub_results: 多 Agent 场景下各子 Agent 的独立结果。
    """

    answer: str
    tools_called: list[str] = field(default_factory=list)
    session_id: str = ""
    latency_ms: int = 0
    pipeline_type: str = ""
    sub_results: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """将结果转换为字典，便于 JSON 序列化。"""
        return {
            "answer": self.answer,
            "tools_called": self.tools_called,
            "session_id": self.session_id,
            "latency_ms": self.latency_ms,
            "pipeline_type": self.pipeline_type,
            "sub_results": self.sub_results,
        }


@dataclass
class StreamEvent:
    """流式 SSE 事件，与前端约定的事件类型对齐。

    type 枚举值：
        answer      -- LLM token chunk
        thinking    -- 思考型模型的思考片段
        tool_start  -- 工具调用开始
        tool_end    -- 工具调用结束
        tool_error  -- 工具调用出错
        __done__    -- 对话完成（含完整 AgentResult 字段）
        __error__   -- 不可恢复错误

    Attributes:
        type: 事件类型字符串。
        content: answer/thinking 事件携带的文本片段。
        tool: tool_start/tool_end/tool_error 事件携带的工具名称。
        output: tool_end 事件携带的工具返回值。
        message: tool_error/__error__ 事件携带的错误描述。
        answer: __done__ 事件携带的完整回答。
        tools_called: __done__ 事件携带的工具调用列表。
        session_id: __done__ 事件携带的会话 ID。
        latency_ms: __done__ 事件携带的总耗时。
    """

    type: str
    content: str | None = None
    tool: str | None = None
    output: str | None = None
    message: str | None = None
    answer: str | None = None
    tools_called: list[str] | None = None
    session_id: str | None = None
    latency_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """返回非 None 字段的字典，用于 SSE JSON 序列化。"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class BaseNode(ABC):
    """Agent 执行节点抽象基类。

    所有具体 Agent 节点（SingleAgentNode、MultiAgentNode）必须继承此类
    并实现 execute 和 stream 两个抽象方法。
    """

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """执行 Agent 并返回完整结果（非流式）。

        Args:
            context: 包含查询、池引用等的执行上下文。

        Returns:
            包含最终回答和元数据的 AgentResult。
        """

    @abstractmethod
    async def stream(self, context: AgentContext) -> AsyncIterator[StreamEvent]:
        """流式执行 Agent，逐事件 yield。

        Args:
            context: 包含查询、池引用等的执行上下文。

        Yields:
            StreamEvent 实例，类型见 StreamEvent.type 枚举。
        """
        # 声明为 async generator 以满足类型检查
        return
        yield  # type: ignore[misc]
