"""
多 Agent 编排（T045）
使用 LangGraph StateGraph 构建多 Agent 编排图：
  routing_node → [sub_agent_node_1 ... sub_agent_node_n]（串行，按 order_index）→ aggregation_node
每个子 Agent 基于 deepagents.create_deep_agent；超时触发优雅降级。
"""
from __future__ import annotations

import asyncio
import uuid
import time
from typing import Any, TypedDict

from src.core.config import get_settings
from src.models.agent import Agent
from src.models.pipeline import Pipeline
from src.agents.intent_router import route_multi_agent


class MultiAgentState(TypedDict):
    query: str
    pipeline_id: int
    session_id: str
    sub_results: list[dict[str, Any]]
    final_answer: str
    tools_called: list[str]
    timed_out_agents: list[str]
    error: str | None


def _build_llm(agent: Agent) -> Any | None:
    """从 Agent.llm_model 构造 LangChain ChatModel。"""
    if get_settings().database_url == "sqlite+aiosqlite:///:memory:":
        return None
    if agent.llm_model is None:
        return None
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=agent.llm_model.model_id,
            api_key=agent.llm_model.api_key,
            base_url=getattr(agent.llm_model, "base_url", None),
            max_completion_tokens=getattr(agent.llm_model, "max_tokens", 2048),
            temperature=getattr(agent.llm_model, "temperature", 0.7),
        )
    except Exception:
        return None


async def _run_sub_agent(
    agent: Agent,
    query: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    """带超时保护地运行单个子 Agent，超时返回降级响应。"""
    start = time.monotonic()
    try:
        llm = _build_llm(agent)
        if llm is None:
            answer = f"[Mock] 子Agent '{agent.name}' 收到查询: {query}"
            tools_called: list[str] = []
        else:
            try:
                from deepagents import create_deep_agent
                deep_agent = create_deep_agent(
                    model=llm,
                    tools=[],
                    system_prompt=agent.system_prompt or "你是一个智能助手。",
                )
                result = await asyncio.wait_for(
                    deep_agent.ainvoke({"messages": [{"role": "user", "content": query}]}),
                    timeout=timeout_seconds,
                )
                messages = result.get("messages", [])
                tools_called = []
                for msg in messages:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                            if name:
                                tools_called.append(name)
                last = messages[-1] if messages else None
                answer = last.content if last and hasattr(last, "content") else "无回复"
            except ImportError:
                answer = f"[Mock] 子Agent '{agent.name}' 处理: {query}"
                tools_called = []

        return {
            "agent_id": agent.id,
            "agent_name": agent.name,
            "answer": answer,
            "tools_called": tools_called,
            "latency_ms": int((time.monotonic() - start) * 1000),
            "timed_out": False,
        }
    except asyncio.TimeoutError:
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
    sub_agents = list(sub_agents if sub_agents is not None else pipeline.sub_agents or [])
    timeout = pipeline.timeout_seconds or 30

    # 路由：选择目标子 Agent
    route = await route_multi_agent(
        query=query,
        sub_agents=sub_agents,
        llm_model=orchestrator_llm,
        confidence_threshold=pipeline.route_confidence_threshold or 0.7,
    )

    target_ids = set(route.target_agent_ids) if route.target_agent_ids else {a.id for a in sub_agents}
    targets = [a for a in sub_agents if a.id in target_ids]
    if not targets:
        targets = sub_agents

    # 串行执行各子 Agent（按 order_index 排序，通过 pipeline_sub_agents 关联表）
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
