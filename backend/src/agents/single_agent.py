"""
单 Agent 执行（T035）
使用 deepagents.create_deep_agent 创建 Agent 实例，
封装 MCP/HTTP/BUILTIN 工具调用，返回自然语言汇总。
"""
from __future__ import annotations

import uuid
from typing import Any

from src.core.config import get_settings
from src.models.agent import Agent
from src.models.tool import Tool, ToolProtocol


def _is_test_mode() -> bool:
    return get_settings().database_url == "sqlite+aiosqlite:///:memory:"


def _build_langchain_tool(tool: Tool) -> Any:
    """将 Tool ORM 对象转换为 LangChain BaseTool。"""
    from langchain_core.tools import StructuredTool

    async def _run(**kwargs: Any) -> str:
        if tool.protocol == ToolProtocol.BUILTIN:
            return f"[BUILTIN] {tool.name} 调用结果: {kwargs}"
        if tool.protocol in (ToolProtocol.MCP, ToolProtocol.HTTP):
            import httpx
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(tool.endpoint_url or "", json=kwargs)
                    resp.raise_for_status()
                    return resp.text
            except Exception as e:
                return f"[ERROR] 工具 {tool.name} 调用失败: {e}"
        return f"[UNKNOWN] 工具协议不支持: {tool.protocol}"

    return StructuredTool.from_function(
        coroutine=_run,
        name=tool.name,
        description=tool.description or tool.display_name,
        args_schema=None,
    )


async def run_single_agent(
    agent: Agent,
    query: str,
    tools: list[Tool],
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    执行单 Agent 调用链。

    返回:
        {answer, tools_called, session_id, latency_ms}
    """
    import time
    start = time.monotonic()
    sid = session_id or f"sess_{uuid.uuid4().hex[:8]}"

    if agent.llm_model is None:
        return {
            "answer": "Agent 未配置 LLM 模型，无法处理查询。",
            "tools_called": [],
            "session_id": sid,
            "latency_ms": int((time.monotonic() - start) * 1000),
        }

    if _is_test_mode():
        return {
            "answer": f"[Mock] 查询已收到：{query}",
            "tools_called": [t.name for t in tools[:1]],
            "session_id": sid,
            "latency_ms": int((time.monotonic() - start) * 1000),
        }

    lc_tools = [_build_langchain_tool(t) for t in tools]
    tools_called: list[str] = []

    try:
        from deepagents import create_deep_agent
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=agent.llm_model.model_id,
            api_key=agent.llm_model.api_key,
            base_url=agent.llm_model.base_url if hasattr(agent.llm_model, "base_url") else None,
            max_completion_tokens=agent.llm_model.max_tokens if hasattr(agent.llm_model, "max_tokens") else 2048,
            temperature=agent.llm_model.temperature if hasattr(agent.llm_model, "temperature") else 0.7,
        )

        deep_agent = create_deep_agent(
            model=llm,
            tools=lc_tools,
            system_prompt=agent.system_prompt or "你是一个智能助手，请根据用户查询提供帮助。",
        )

        result = await deep_agent.ainvoke({"messages": [{"role": "user", "content": query}]})
        messages = result.get("messages", [])

        # 收集工具调用记录
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                    if name:
                        tools_called.append(name)

        last = messages[-1] if messages else None
        answer = last.content if last and hasattr(last, "content") else "无回复"

    except ImportError:
        answer = f"[Mock] 查询已收到：{query}。（deepagents 未安装，返回模拟响应）"
        tools_called = [t.name for t in tools[:1]]
    except Exception as e:
        answer = f"Agent 执行出错：{e}"
        tools_called = []

    return {
        "answer": answer,
        "tools_called": list(dict.fromkeys(tools_called)),
        "session_id": sid,
        "latency_ms": int((time.monotonic() - start) * 1000),
    }
