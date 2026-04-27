"""
单 Agent 执行（T035）
使用 deepagents.create_deep_agent 创建 Agent 实例，
封装 MCP/HTTP/BUILTIN 工具调用，返回自然语言汇总。
"""
from __future__ import annotations

import base64
import uuid
from typing import Any

from src.models.agent import Agent
from src.models.tool import Tool, ToolProtocol, ToolAuthType


def _tool_auth_headers(tool: Tool) -> dict[str, str]:
    """从 Tool 的 auth_type/auth_config 构造 HTTP 请求头。"""
    auth = tool.auth_config or {}
    if tool.auth_type == ToolAuthType.BEARER_TOKEN:
        return {"Authorization": f"Bearer {auth.get('token', '')}"}
    if tool.auth_type == ToolAuthType.API_KEY and auth.get("key_location", "header") == "header":
        return {auth.get("key_name", "X-API-Key"): auth.get("key_value", "")}
    if tool.auth_type == ToolAuthType.BASIC_AUTH:
        creds = f"{auth.get('username', '')}:{auth.get('password', '')}"
        return {"Authorization": f"Basic {base64.b64encode(creds.encode()).decode()}"}
    return {}


def _tool_auth_params(tool: Tool) -> dict[str, str]:
    """从 Tool 的 auth_config 构造 Query 参数（API_KEY query 模式）。"""
    auth = tool.auth_config or {}
    if tool.auth_type == ToolAuthType.API_KEY and auth.get("key_location") == "query":
        return {auth.get("key_name", "api_key"): auth.get("key_value", "")}
    return {}


async def _call_mcp_tool(endpoint_url: str, headers: dict, tool_name: str, arguments: dict) -> str:
    """
    通过 MCP JSON-RPC 2.0 协议调用工具。
    使用 streamable_http_client + ClientSession.call_tool()。
    """
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as http_client:
        async with streamable_http_client(endpoint_url, http_client=http_client) as (
            read_stream, write_stream, _
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)

    parts: list[str] = []
    for item in result.content:
        if hasattr(item, "text"):
            parts.append(item.text)
        elif isinstance(item, dict):
            import json
            parts.append(json.dumps(item, ensure_ascii=False))
        else:
            parts.append(str(item))
    return "\n".join(parts) or "[工具返回空结果]"


async def _call_http_tool(tool: Tool, kwargs: dict) -> str:
    """通过 HTTP POST 调用工具，支持 auth_type 认证。"""
    import httpx
    headers = _tool_auth_headers(tool)
    params = _tool_auth_params(tool)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            tool.endpoint_url or "",
            json=kwargs,
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        return resp.text


def _build_langchain_tool(tool: Tool) -> Any:
    """将 Tool ORM 对象转换为 LangChain StructuredTool。"""
    from langchain_core.tools import StructuredTool

    async def _run(**kwargs: Any) -> str:
        try:
            if tool.protocol == ToolProtocol.MCP:
                # MCP 工具：优先使用 mcp_server 的 endpoint；tool 本身的 endpoint 作兜底
                server = tool.mcp_server  # 已通过 selectinload 预加载
                if server and server.endpoint_url:
                    from src.services.mcp_server_service import MCPServerService
                    headers = MCPServerService.build_header(server)
                    endpoint = server.endpoint_url
                else:
                    endpoint = tool.endpoint_url or ""
                    headers = _tool_auth_headers(tool)
                tool_name = tool.mcp_tool_name or tool.name
                return await _call_mcp_tool(endpoint, headers, tool_name, kwargs)

            if tool.protocol == ToolProtocol.HTTP:
                return await _call_http_tool(tool, kwargs)

            if tool.protocol == ToolProtocol.BUILTIN:
                return f"[BUILTIN] 工具 {tool.name} 为内置函数，需在运行时注册后才能调用。"

            return f"[ERROR] 未支持的工具协议: {tool.protocol}"
        except Exception as e:
            return f"[ERROR] 工具 {tool.name} 调用失败: {e}"

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

    lc_tools = [_build_langchain_tool(t) for t in tools]
    tools_called: list[str] = []

    try:
        from deepagents import create_deep_agent
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=agent.llm_model.model_id,
            api_key=agent.llm_model.api_key,
            base_url=agent.llm_model.endpoint_url or None,
            temperature=agent.temperature,
            max_completion_tokens=agent.max_tokens,
        )

        deep_agent = create_deep_agent(
            model=llm,
            tools=lc_tools,
            system_prompt=agent.system_prompt or "你是一个智能助手，请根据用户查询提供帮助。",
        )

        result = await deep_agent.ainvoke({"messages": [{"role": "user", "content": query}]})
        messages = result.get("messages", [])

        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                    if name:
                        tools_called.append(name)

        last = messages[-1] if messages else None
        answer = last.content if last and hasattr(last, "content") else "无回复"

    except Exception as e:
        answer = f"Agent 执行出错：{e}"
        tools_called = []

    return {
        "answer": answer,
        "tools_called": list(dict.fromkeys(tools_called)),
        "session_id": sid,
        "latency_ms": int((time.monotonic() - start) * 1000),
    }
