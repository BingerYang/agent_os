"""
多 Agent 编排（T045）
使用 LangGraph StateGraph 构建多 Agent 编排图：
  routing_node → [sub_agent_node_1 ... sub_agent_node_n]（串行，按 order_index）→ aggregation_node
每个子 Agent 基于 deepagents.create_deep_agent；超时触发优雅降级。
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any, TypedDict

from src.agents.intent_router import route_multi_agent
from src.agents.single_agent import _build_tools_with_real_mcp_schemas
from src.models.agent import Agent
from src.models.pipeline import Pipeline

logger = logging.getLogger()

class MultiAgentState(TypedDict):
    query: str
    pipeline_id: int
    session_id: str
    sub_results: list[dict[str, Any]]
    final_answer: str
    tools_called: list[str]
    timed_out_agents: list[str]
    error: str | None


def _build_llm(agent: Agent) -> Any:
    """从 Agent.llm_model 构造 LangChain ChatModel。失败时抛出异常而非静默返回 None。"""
    if agent.llm_model is None:
        raise ValueError(f"Agent '{agent.name}' 未配置 LLM 模型")
    from langchain_openai import ChatOpenAI

    from src.services.llm_model_service import decrypt_api_key
    return ChatOpenAI(
        model=agent.llm_model.model_id,
        api_key=decrypt_api_key(agent.llm_model.api_key),
        base_url=getattr(agent.llm_model, "endpoint_url", None),
        temperature=getattr(agent, "temperature", 0.7),
        max_completion_tokens=getattr(agent, "max_tokens", 2048),
    )


async def _run_sub_agent(
        agent: Agent,
        query: str,
        timeout_seconds: int,
) -> dict[str, Any]:
    """带超时保护地运行单个子 Agent，超时返回降级响应。"""
    start = time.monotonic()
    try:
        from deepagents import create_deep_agent


        llm = _build_llm(agent)
        lc_tools = await _build_tools_with_real_mcp_schemas(agent.tools or [])
        deep_agent = create_deep_agent(
            model=llm,
            tools=lc_tools,
            system_prompt=agent.system_prompt or "你是一个智能助手。",
        )
        result = await asyncio.wait_for(
            deep_agent.ainvoke({"messages": [{"role": "user", "content": query}]}),
            timeout=timeout_seconds,
        )
        messages = result.get("messages", [])
        tools_called: list[str] = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                    if name:
                        tools_called.append(name)
        last = messages[-1] if messages else None
        answer = last.content if last and hasattr(last, "content") else "无回复"

        return {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "answer": answer,
            "tools_called": tools_called,
            "latency_ms": int((time.monotonic() - start) * 1000),
            "timed_out": False,
        }
    except TimeoutError:
        return {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "answer": f"[降级] 子Agent '{agent.name}' 超时，无法提供回复。",
            "tools_called": [],
            "latency_ms": int((time.monotonic() - start) * 1000),
            "timed_out": True,
        }
    except Exception as e:
        return {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "answer": f"[错误] 子Agent '{agent.name}' 执行失败: {e}",
            "tools_called": [],
            "latency_ms": int((time.monotonic() - start) * 1000),
            "timed_out": False,
        }


async def _aggregate_results(
        results: list[dict[str, Any]],
        query: str,
        orchestrator_llm: Any | None,
) -> str:
    """聚合多个子 Agent 的结果，生成最终回复。"""
    if not results:
        return "未获得任何子 Agent 的回复。"

    valid = [r for r in results if not r["timed_out"]]
    if len(valid) == 1:
        return valid[0]["answer"]

    if not valid:
        return "所有子 Agent 均超时，无法提供回复。"

    # 多结果汇总
    combined = "\n\n".join(
        f"【{r['agent_name']}的回复】\n{r['answer']}" for r in valid
    )

    if orchestrator_llm is None:
        return f"综合多个子Agent的回复：\n\n{combined}"

    try:
        summary_prompt = (
            f"以下是多个子Agent针对用户问题「{query}」的回复，"
            f"请综合整理成一个完整、流畅的最终回复：\n\n{combined}"
        )
        result = await orchestrator_llm.ainvoke(summary_prompt)
        return result.content if hasattr(result, "content") else str(result)
    except Exception:
        return combined


async def run_multi_agent(
        pipeline: Pipeline,
        query: str,
        session_id: str | None = None,
        sub_agents: list[Agent] | None = None,
        orchestrator: Agent | None = None,
) -> dict[str, Any]:
    """
    执行多 Agent 流水线。

    返回:
        {answer, pipeline_type, tools_called, session_id, latency_ms, sub_results}
    """
    start = time.monotonic()
    sid = session_id or f"sess_{uuid.uuid4().hex[:8]}"

    orchestrator = orchestrator if orchestrator is not None else pipeline.primary_agent
    orchestrator_llm = _build_llm(orchestrator) if orchestrator else None
    sub_agents = list(sub_agents or [])
    timeout = pipeline.timeout_seconds or 30

    # 路由：选择目标子 Agent
    route = await route_multi_agent(
        query=query,
        sub_agents=sub_agents,
        llm_model=orchestrator_llm,
        confidence_threshold=pipeline.route_confidence_threshold or 0.7,
    )

    target_ids = set(route.target_agent_ids) if route.target_agent_ids else {a.id for a in sub_agents}
    logger.info(f"Routing {query} to {target_ids}")
    targets = [a for a in sub_agents if a.id in target_ids]
    if not targets:
        targets = sub_agents

    # 串行执行各子 Agent
    sub_results: list[dict[str, Any]] = []
    for agent in targets:
        result = await _run_sub_agent(agent, query, timeout)
        sub_results.append(result)

    # 聚合
    final_answer = await _aggregate_results(sub_results, query, orchestrator_llm)

    all_tools: list[str] = []
    for r in sub_results:
        all_tools.extend(r.get("tools_called", []))

    return {
        "answer": final_answer,
        "pipeline_type": "MULTI_AGENT",
        "tools_called": list(dict.fromkeys(all_tools)),
        "session_id": sid,
        "latency_ms": int((time.monotonic() - start) * 1000),
        "sub_results": sub_results,
    }


# ---------------------------------------------------------------------------
# BaseNode 实现：多 Agent 编排节点（T027）
# ---------------------------------------------------------------------------

class _PoolAgentRef:
    """将 AgentPoolEntry 适配为 route_multi_agent 期望的接口（含 .id / .name）。"""

    def __init__(self, agent_id: int, system_prompt: str) -> None:
        self.id = agent_id
        self.name = system_prompt[:60].strip() or f"agent_{agent_id}"


class MultiAgentNode:
    """BaseNode 实现：多 Agent 编排，支持单路由真实流式输出。

    流式优化：若路由结果仅指向单个子 Agent（is_single=True）且置信度
    达到阈值，直接将请求转发给 SingleAgentNode.stream()，实现 token 级
    流式输出；否则批量执行后推送最终答案。
    """

    async def execute(self, context: AgentContext) -> AgentResult:
        """非流式执行，聚合全部子 Agent 结果后返回。"""
        import time

        from src.agents.base import AgentResult

        start = time.monotonic()
        orchestrator_entry = context.agent_pool.get(context.pipeline_config.primary_agent_id)
        if orchestrator_entry is None:
            return AgentResult(
                answer="主 Agent 未加载",
                session_id=context.session_id,
                pipeline_type="MULTI_AGENT",
            )

        sub_entries = [
            context.agent_pool.get(sid)
            for sid in orchestrator_entry.sub_agent_ids
            if context.agent_pool.get(sid) is not None
        ]
        sub_refs = [_PoolAgentRef(e.agent_id, e.system_prompt) for e in sub_entries if e]
        timeout = orchestrator_entry.timeout_seconds

        route = await route_multi_agent(
            query=context.query,
            sub_agents=sub_refs,
            llm_model=None,  # 不持有原始 LLM，降级为全选
            confidence_threshold=orchestrator_entry.route_confidence_threshold,
        )
        target_ids = set(route.target_agent_ids) if route.target_agent_ids else {e.agent_id for e in sub_entries if e}
        targets = [e for e in sub_entries if e and e.agent_id in target_ids]

        sub_results: list[dict] = []
        for entry in targets:
            sub_result = await self._run_pool_agent(entry, context.query, timeout)
            sub_results.append(sub_result)

        all_tools: list[str] = []
        for r in sub_results:
            all_tools.extend(r.get("tools_called", []))

        final_answer = await _aggregate_results(sub_results, context.query, None)
        return AgentResult(
            answer=final_answer,
            tools_called=list(dict.fromkeys(all_tools)),
            session_id=context.session_id,
            latency_ms=int((time.monotonic() - start) * 1000),
            pipeline_type="MULTI_AGENT",
            sub_results=sub_results,
        )

    async def stream(self, context: AgentContext) -> AsyncIterator[StreamEvent]:  # type: ignore[override]
        """流式执行：单路由 → 转发 SingleAgentNode.stream()；多路由 → 批量后推送。"""
        import time

        from src.agents.base import StreamEvent
        from src.agents.single_agent import SingleAgentNode
        from src.runtime.context import PipelineCacheEntry

        start = time.monotonic()
        orchestrator_entry = context.agent_pool.get(context.pipeline_config.primary_agent_id)
        if orchestrator_entry is None:
            yield StreamEvent(
                type="__done__",
                answer="主 Agent 未加载",
                tools_called=[],
                session_id=context.session_id,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
            return

        sub_entries = [
            e for sid in orchestrator_entry.sub_agent_ids
            if (e := context.agent_pool.get(sid)) is not None
        ]
        sub_refs = [_PoolAgentRef(e.agent_id, e.system_prompt) for e in sub_entries]
        threshold = orchestrator_entry.route_confidence_threshold

        route = await route_multi_agent(
            query=context.query,
            sub_agents=sub_refs,
            llm_model=None,
            confidence_threshold=threshold,
        )

        # 单路由且置信度足够 → 真实 token 级流式
        use_single_stream = (
            (route.is_single and route.confidence >= threshold)
            or len(sub_entries) == 1
        )
        if use_single_stream and sub_entries:
            target_id = route.target_agent_ids[0] if route.target_agent_ids else sub_entries[0].agent_id
            sub_cfg = PipelineCacheEntry(
                pipeline_uid=context.pipeline_config.pipeline_uid,
                pipeline_id=context.pipeline_config.pipeline_id,
                pipeline_type="SINGLE_AGENT",
                primary_agent_id=target_id,
            )
            sub_ctx = type(context)(
                query=context.query,
                session_id=context.session_id,
                pipeline_config=sub_cfg,
                agent_pool=context.agent_pool,
                tool_pool=context.tool_pool,
                mcp_pool=context.mcp_pool,
            )
            async for event in SingleAgentNode().stream(sub_ctx):
                yield event
            return

        # 多路由 → 批量执行后一次性推送
        result = await self.execute(context)
        yield StreamEvent(type="answer", content=result.answer)
        yield StreamEvent(
            type="__done__",
            answer=result.answer,
            tools_called=result.tools_called,
            session_id=result.session_id,
            latency_ms=result.latency_ms,
        )

    @staticmethod
    async def _run_pool_agent(entry: Any, query: str, timeout: int) -> dict:
        """带超时保护地通过已编译图执行子 Agent。"""
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                entry.compiled_graph.ainvoke(
                    {"messages": [{"role": "user", "content": query}]}
                ),
                timeout=timeout,
            )
            messages = result.get("messages", [])
            tools_called: list[str] = []
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                        if name:
                            tools_called.append(name)
            last = messages[-1] if messages else None
            answer = last.content if last and hasattr(last, "content") else "无回复"
            return {
                "agent_id": entry.agent_id,
                "agent_name": f"agent_{entry.agent_id}",
                "answer": answer,
                "tools_called": tools_called,
                "latency_ms": int((time.monotonic() - start) * 1000),
                "timed_out": False,
            }
        except TimeoutError:
            return {
                "agent_id": entry.agent_id,
                "agent_name": f"agent_{entry.agent_id}",
                "answer": f"[降级] 子 Agent {entry.agent_id} 超时，无法提供回复。",
                "tools_called": [],
                "latency_ms": int((time.monotonic() - start) * 1000),
                "timed_out": True,
            }
        except Exception as e:
            return {
                "agent_id": entry.agent_id,
                "agent_name": f"agent_{entry.agent_id}",
                "answer": f"[错误] 子 Agent {entry.agent_id} 执行失败: {e}",
                "tools_called": [],
                "latency_ms": int((time.monotonic() - start) * 1000),
                "timed_out": False,
            }


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from src.agents.base import AgentContext, AgentResult, StreamEvent  # noqa: F401
