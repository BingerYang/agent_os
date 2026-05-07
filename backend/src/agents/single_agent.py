"""
单 Agent 执行（T035）
使用 deepagents.create_deep_agent 创建 Agent 实例，
封装 MCP/HTTP/BUILTIN 工具调用，返回自然语言汇总。
"""
from __future__ import annotations

import base64
import logging
import re
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from pydantic import Field as PydanticField
from pydantic import create_model

from src.models.agent import Agent
from src.models.tool import Tool, ToolAuthType, ToolProtocol

logger = logging.getLogger()


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


def build_system_prompt(src_prompt: str):
    return src_prompt.format(current_date=datetime.now().strftime("%Y-%m-%d"))


def _schema_to_python_type(schema: dict[str, Any] | None) -> Any:
    """Convert a subset of JSON Schema types into Pydantic-compatible annotations."""
    if not isinstance(schema, dict):
        return Any

    if "anyOf" in schema or "oneOf" in schema or "allOf" in schema:
        return Any

    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        non_null_types = [item for item in schema_type if item != "null"]
        if len(non_null_types) == 1:
            schema_type = non_null_types[0]
        else:
            return Any

    if schema_type == "string":
        return str
    if schema_type == "integer":
        return int
    if schema_type == "number":
        return float
    if schema_type == "boolean":
        return bool
    if schema_type == "array":
        return list[_schema_to_python_type(schema.get("items"))]
    if schema_type == "object":
        return dict[str, Any]
    return Any


def _build_args_schema(tool_name: str, json_schema: dict[str, Any] | None) -> type[Any] | None:
    """Build a Pydantic model from MCP inputSchema for StructuredTool.args_schema."""
    if not isinstance(json_schema, dict):
        return None

    properties = json_schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return None

    required = set(json_schema.get("required", []))
    field_defs: dict[str, tuple[Any, Any]] = {}

    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            field_schema = {}

        annotation = _schema_to_python_type(field_schema)
        default = ... if field_name in required else field_schema.get("default", None)
        field_defs[field_name] = (
            annotation,
            PydanticField(default=default, description=field_schema.get("description")),
        )

    if not field_defs:
        return None

    model_name = "".join(part.capitalize() for part in re.split(r"[^0-9A-Za-z]+", tool_name) if part) or "Tool"
    return create_model(f"{model_name}Args", **field_defs)


async def _build_tools_with_real_mcp_schemas(tools: list[Tool]) -> list[Any]:
    """Build LangChain tools; for MCP tools fetch real input schema from the server."""
    import httpx
    from langchain_core.tools import StructuredTool
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    from src.services.mcp_server_service import MCPServerService

    # Partition tools
    mcp_server_map: dict[str, tuple[dict, list[Tool]]] = {}
    other_tools: list[Tool] = []

    for tool in tools:
        if tool.protocol == ToolProtocol.MCP and tool.mcp_server and tool.mcp_server.endpoint_url:
            key = tool.mcp_server.endpoint_url
            if key not in mcp_server_map:
                mcp_server_map[key] = (MCPServerService.build_header(tool.mcp_server), [])
            mcp_server_map[key][1].append(tool)
        else:
            other_tools.append(tool)

    result: list[Any] = [_build_langchain_tool(t) for t in other_tools]

    for endpoint, (headers, server_tools) in mcp_server_map.items():
        # Map mcp_tool_name -> local Tool
        name_map: dict[str, Tool] = {(t.mcp_tool_name or t.name): t for t in server_tools}
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as http_client:
                async with streamable_http_client(endpoint, http_client=http_client) as (
                        read_stream, write_stream, _
                ):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        tool_list = await session.list_tools()

            matched: set[str] = set()
            for tool_def in tool_list.tools:
                if tool_def.name not in name_map:
                    continue
                matched.add(tool_def.name)
                local_tool = name_map[tool_def.name]
                real_schema: dict = getattr(tool_def, "inputSchema", None) or {}
                args_schema = _build_args_schema(local_tool.name, real_schema)

                _ep = endpoint
                _hd = headers
                _mn = tool_def.name

                async def _run(_e: str = _ep, _h: dict = _hd, _n: str = _mn, **kwargs: Any) -> str:
                    try:
                        res = await _call_mcp_tool(_e, _h, _n, kwargs)
                        return res
                    except Exception as ex:
                        return f"[ERROR] 工具 {_n} 调用失败: {ex}"

                result.append(StructuredTool.from_function(
                    coroutine=_run,
                    name=local_tool.name,
                    description=tool_def.description or local_tool.description or local_tool.display_name,
                    args_schema=args_schema,
                ))

            # Fallback for tools not found on server
            for mcp_name, local_tool in name_map.items():
                if mcp_name not in matched:
                    result.append(_build_langchain_tool(local_tool))

        except Exception:
            # Server unreachable – fall back to local schema
            for t in server_tools:
                result.append(_build_langchain_tool(t))

    return result


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

    lc_tools = await _build_tools_with_real_mcp_schemas(tools)
    tools_called: list[str] = []

    try:
        from deepagents import create_deep_agent
        from langchain_openai import ChatOpenAI

        from src.services.llm_model_service import decrypt_api_key

        llm = ChatOpenAI(
            model=agent.llm_model.model_id,
            api_key=decrypt_api_key(agent.llm_model.api_key),
            base_url=agent.llm_model.endpoint_url or None,
            temperature=agent.temperature,
            max_completion_tokens=agent.max_tokens,
        )

        deep_agent = create_deep_agent(
            model=llm,
            tools=lc_tools,
            system_prompt=build_system_prompt(agent.system_prompt or "你是一个智能助手，请根据用户查询提供帮助。"),
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


async def stream_single_agent(
        agent: Agent,
        query: str,
        tools: list[Tool],
        session_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """
    流式执行单 Agent，逐事件 yield：
    - {type: "thinking",   content: str}   ← 思考型模型专属
    - {type: "answer",     content: str}   ← LLM token chunk
    - {type: "tool_start", tool: str}
    - {type: "tool_end",   tool: str, output: str}
    - {type: "tool_error", tool: str, message: str}
    - {type: "__done__",   answer, thinking, tools_called, session_id, latency_ms}
    - {type: "__error__",  message: str}
    """
    import time
    start = time.monotonic()
    sid = session_id or f"sess_{uuid.uuid4().hex[:8]}"

    if agent.llm_model is None:
        yield {"type": "__done__", "answer": "Agent 未配置 LLM 模型，无法处理查询。",
               "thinking": "", "tools_called": [], "session_id": sid,
               "latency_ms": int((time.monotonic() - start) * 1000)}
        return

    lc_tools = await _build_tools_with_real_mcp_schemas(tools)
    accumulated_answer = ""
    accumulated_thinking = ""
    tools_called: list[str] = []

    try:
        from deepagents import create_deep_agent
        from langchain_openai import ChatOpenAI

        from src.services.llm_model_service import decrypt_api_key

        llm = ChatOpenAI(
            model=agent.llm_model.model_id,
            api_key=decrypt_api_key(agent.llm_model.api_key),
            base_url=agent.llm_model.endpoint_url or None,
            temperature=agent.temperature,
            max_completion_tokens=agent.max_tokens,
            streaming=True,
        )

        deep_agent = create_deep_agent(
            model=llm,
            tools=lc_tools,
            system_prompt=build_system_prompt(agent.system_prompt or "你是一个智能助手，请根据用户查询提供帮助。"),
        )

        async for event in deep_agent.astream_events(
                {"messages": [{"role": "user", "content": query}]},
                version="v2",
        ):
            etype = event.get("event", "")

            if etype == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk is None:
                    continue
                content = chunk.content
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if item.get("type") == "thinking":
                            text = item.get("thinking", "")
                            if text:
                                accumulated_thinking += text
                                yield {"type": "thinking", "content": text}
                        elif item.get("type") == "text":
                            text = item.get("text", "")
                            if text:
                                accumulated_answer += text
                                yield {"type": "answer", "content": text}
                elif isinstance(content, str) and content:
                    accumulated_answer += content
                    yield {"type": "answer", "content": content}

            elif etype == "on_tool_start":
                tool_name = event.get("name", "")
                if tool_name:
                    logger.info("Tool started: %s", tool_name)
                    yield {"type": "tool_start", "tool": tool_name}

            elif etype == "on_tool_end":
                tool_name = event.get("name", "")
                if tool_name:
                    tools_called.append(tool_name)
                    raw_output = event.get("data", {}).get("output")
                    if hasattr(raw_output, "content"):
                        tool_output = raw_output.content
                    elif raw_output is not None:
                        tool_output = str(raw_output)
                    else:
                        tool_output = ""
                    is_error = isinstance(tool_output, str) and tool_output.startswith("[ERROR]")
                    yield {"type": "tool_end", "tool": tool_name, "output": tool_output}
                    if is_error:
                        yield {"type": "tool_error", "tool": tool_name, "message": tool_output}
                        logger.warning("Tool error: %s => %s", tool_name, tool_output)
                    else:
                        logger.info("Tool ended: %s => %s", tool_name, tool_output[:200] if tool_output else "")

    except Exception as e:
        logger.exception(e)
        yield {"type": "__error__", "message": f"Agent 执行出错：{e}"}
        return

    yield {
        "type": "__done__",
        "answer": accumulated_answer or "（无回复）",
        "thinking": accumulated_thinking,
        "tools_called": list(dict.fromkeys(tools_called)),
        "session_id": sid,
        "latency_ms": int((time.monotonic() - start) * 1000),
    }


# ---------------------------------------------------------------------------
# BaseNode 实现：使用 AgentPool 中的预编译图（T026）
# ---------------------------------------------------------------------------

class SingleAgentNode:
    """BaseNode 实现：复用 AgentPool 中的预编译图，零数据库读取。

    工具列表已在 AgentPool.build_entry 时注入 compiled_graph，
    无需每次重新构建；MCP 调用通过 MCPConnectionPool 复用长连接。
    """

    async def execute(self, context: AgentContext) -> AgentResult:
        """非流式执行，返回完整 AgentResult。"""
        import time

        from src.agents.base import AgentResult

        start = time.monotonic()
        entry = context.agent_pool.get(context.pipeline_config.primary_agent_id)
        if entry is None:
            return AgentResult(
                answer="Agent 未加载（未发布或池中不存在）",
                session_id=context.session_id,
                pipeline_type="SINGLE_AGENT",
            )

        tools_called: list[str] = []
        try:
            result = await entry.compiled_graph.ainvoke(
                {"messages": [{"role": "user", "content": context.query}]}
            )
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

        return AgentResult(
            answer=answer,
            tools_called=list(dict.fromkeys(tools_called)),
            session_id=context.session_id,
            latency_ms=int((time.monotonic() - start) * 1000),
            pipeline_type="SINGLE_AGENT",
        )

    async def stream(self, context: AgentContext) -> AsyncIterator[StreamEvent]:  # type: ignore[override]
        """流式执行，逐事件 yield StreamEvent。"""
        import time

        from src.agents.base import StreamEvent

        start = time.monotonic()
        entry = context.agent_pool.get(context.pipeline_config.primary_agent_id)
        if entry is None:
            yield StreamEvent(
                type="__done__",
                answer="Agent 未加载（未发布或池中不存在）",
                tools_called=[],
                session_id=context.session_id,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
            return

        accumulated_answer = ""
        tools_called: list[str] = []

        try:
            async for event in entry.compiled_graph.astream_events(
                {"messages": [{"role": "user", "content": context.query}]},
                version="v2",
            ):
                etype = event.get("event", "")

                if etype == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk is None:
                        continue
                    content = chunk.content
                    if isinstance(content, list):
                        for item in content:
                            if not isinstance(item, dict):
                                continue
                            if item.get("type") == "thinking":
                                text = item.get("thinking", "")
                                if text:
                                    yield StreamEvent(type="thinking", content=text)
                            elif item.get("type") == "text":
                                text = item.get("text", "")
                                if text:
                                    accumulated_answer += text
                                    yield StreamEvent(type="answer", content=text)
                    elif isinstance(content, str) and content:
                        accumulated_answer += content
                        yield StreamEvent(type="answer", content=content)

                elif etype == "on_tool_start":
                    tool_name = event.get("name", "")
                    if tool_name:
                        yield StreamEvent(type="tool_start", tool=tool_name)

                elif etype == "on_tool_end":
                    tool_name = event.get("name", "")
                    if tool_name:
                        tools_called.append(tool_name)
                        raw_output = event.get("data", {}).get("output")
                        if hasattr(raw_output, "content"):
                            tool_output = raw_output.content
                        elif raw_output is not None:
                            tool_output = str(raw_output)
                        else:
                            tool_output = ""
                        yield StreamEvent(type="tool_end", tool=tool_name, output=tool_output)
                        if isinstance(tool_output, str) and tool_output.startswith("[ERROR]"):
                            yield StreamEvent(type="tool_error", tool=tool_name, message=tool_output)

        except Exception as e:
            yield StreamEvent(type="__error__", message=f"Agent 执行出错：{e}")
            return

        yield StreamEvent(
            type="__done__",
            answer=accumulated_answer or "（无回复）",
            tools_called=list(dict.fromkeys(tools_called)),
            session_id=context.session_id,
            latency_ms=int((time.monotonic() - start) * 1000),
        )


# 延迟类型注解（避免循环导入）
from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from src.agents.base import AgentContext, AgentResult, StreamEvent  # noqa: F401
