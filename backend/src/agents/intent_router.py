"""
意图路由（T034）
使用 LangChain 1.0 create_agent 做意图识别：
  - 判断查询最适合哪些工具
  - 返回工具选择结果供 single_agent 使用
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntentResult:
    selected_tools: list[str] = field(default_factory=list)
    confidence: float = 1.0
    reasoning: str = ""


async def route_intent(query: str, tools: list[Any], llm_model: Any | None = None) -> IntentResult:
    """
    分析查询意图，选择合适工具。

    参数:
        query: 用户查询文本
        tools: 可用工具列表（Tool ORM 对象）
        llm_model: LangChain BaseChatModel 实例（可为 None，则选所有工具）

    返回:
        IntentResult，包含 selected_tools（tool.name 列表）和置信度
    """
    if not tools:
        return IntentResult(selected_tools=[], confidence=1.0)

    if llm_model is None:
        return IntentResult(
            selected_tools=[t.name for t in tools],
            confidence=1.0,
            reasoning="无 LLM 模型，默认选择全部工具",
        )

    try:
        return await _llm_route(query, tools, llm_model)
    except Exception as e:
        return IntentResult(
            selected_tools=[t.name for t in tools],
            confidence=0.5,
            reasoning=f"意图路由失败，降级选择全部工具: {e}",
        )


async def _llm_route(query: str, tools: list[Any], llm_model: Any) -> IntentResult:
    """使用 LangChain 1.0 create_agent 识别意图并选择工具。"""
    from langchain.agents import create_agent

    tool_descriptions = "\n".join(
        f"- {t.name}: {t.description or '无描述'}" for t in tools
    )
    system_prompt = (
        "你是一个工具选择助手。根据用户的查询，从可用工具列表中选择最合适的工具。"
        "只输出工具名称列表，每行一个，不需要解释。如果没有合适工具输出 NONE。"
    )
    user_message = f"可用工具：\n{tool_descriptions}\n\n用户查询：{query}\n\n请选择合适的工具："

    agent = create_agent(
        model=llm_model,
        tools=[],
        system_prompt=system_prompt,
    )
    result = await agent.ainvoke({"messages": [{"role": "user", "content": user_message}]})

    messages = result.get("messages", [])
    last_message = messages[-1] if messages else None
    content = last_message.content if last_message and hasattr(last_message, "content") else ""

    if content.strip().upper() == "NONE" or not content.strip():
        return IntentResult(selected_tools=[], confidence=0.9)

    tool_names = {t.name for t in tools}
    selected = [line.strip() for line in content.strip().splitlines() if line.strip() in tool_names]

    return IntentResult(
        selected_tools=selected or [t.name for t in tools],
        confidence=0.9 if selected else 0.5,
        reasoning=content,
    )


@dataclass
class RouteResult:
    target_agent_ids: list[int]
    confidence: float
    route_reason: str = ""
    is_single: bool = False


async def route_multi_agent(
    query: str,
    sub_agents: list[Any],
    llm_model: Any | None = None,
    confidence_threshold: float = 0.7,
) -> RouteResult:
    """
    多 Agent 路由：分析查询意图，选择目标子 Agent 列表。

    返回:
        RouteResult，包含 target_agent_ids（选中的 Agent id 列表）、置信度、路由理由
    """
    if not sub_agents:
        return RouteResult(target_agent_ids=[], confidence=1.0, route_reason="无子 Agent 可用")

    if llm_model is None:
        return RouteResult(
            target_agent_ids=[a.id for a in sub_agents],
            confidence=0.5,
            route_reason="无 LLM，默认选择全部子 Agent",
        )

    try:
        return await _llm_route_multi(query, sub_agents, llm_model, confidence_threshold)
    except Exception as e:
        return RouteResult(
            target_agent_ids=[a.id for a in sub_agents],
            confidence=0.4,
            route_reason=f"路由失败降级: {e}",
        )


async def _llm_route_multi(
    query: str,
    sub_agents: list[Any],
    llm_model: Any,
    confidence_threshold: float,
) -> RouteResult:
    """使用 LangChain 1.0 create_agent 进行多 Agent 路由选择。"""
    from langchain.agents import create_agent

    agent_descriptions = "\n".join(
        f"- id={a.id}, name={a.name}" for a in sub_agents
    )
    system_prompt = (
        "你是一个 Agent 路由助手。根据用户查询，从候选子 Agent 列表中选择最合适的子 Agent。"
        "只输出被选中的 Agent 的 id（数字），每行一个。如果多个都合适则全部输出。"
    )
    user_message = f"候选子 Agent：\n{agent_descriptions}\n\n用户查询：{query}\n\n请选择合适的子 Agent id："

    agent = create_agent(
        model=llm_model,
        tools=[],
        system_prompt=system_prompt,
    )
    result = await agent.ainvoke({"messages": [{"role": "user", "content": user_message}]})
    messages = result.get("messages", [])
    last = messages[-1] if messages else None
    content = last.content if last and hasattr(last, "content") else ""

    agent_id_map = {str(a.id): a.id for a in sub_agents}
    selected_ids = []
    for line in content.strip().splitlines():
        line = line.strip()
        if line in agent_id_map:
            selected_ids.append(agent_id_map[line])

    if not selected_ids:
        selected_ids = [a.id for a in sub_agents]

    is_single = len(selected_ids) == 1
    confidence = 0.9 if selected_ids != [a.id for a in sub_agents] else 0.6

    return RouteResult(
        target_agent_ids=selected_ids,
        confidence=confidence,
        route_reason=content,
        is_single=is_single,
    )
