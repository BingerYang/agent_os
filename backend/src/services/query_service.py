"""
查询服务（T036 / T046）
支持单 Agent / 多 Agent 流水线编排：
  加载 Pipeline 配置 → PreDetection → Pipeline Dispatch → PostDetection → 构造响应
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import (
    BusinessValidationError,
    PostCheckRejected,
    PreCheckRejected,
    ResourceNotFound,
)
from src.models.pipeline import Pipeline, PipelineType
from src.models.agent import Agent
from src.models.tool import Tool
from src.agents.detection import run_pre_detection, run_post_detection
from src.agents.intent_router import route_intent
from src.agents.single_agent import run_single_agent
from src.services.config_cache import config_cache


async def _load_pipeline(db: AsyncSession, pipeline_uid: str) -> Pipeline:
    q = (
        select(Pipeline)
        .where(Pipeline.uid == pipeline_uid, Pipeline.enabled == True)
        .options(
            selectinload(Pipeline.primary_agent).selectinload(Agent.tools).selectinload(Tool.mcp_server),
            selectinload(Pipeline.primary_agent).selectinload(Agent.skills),
            selectinload(Pipeline.primary_agent).selectinload(Agent.llm_model),
            selectinload(Pipeline.detection_rules),
        )
    )
    pipeline = (await db.execute(q)).scalar_one_or_none()
    if not pipeline:
        raise ResourceNotFound(f"流水线 {pipeline_uid} 不存在或未启用")
    return pipeline


async def _ensure_config_snapshot(db: AsyncSession) -> None:
    if config_cache.is_loaded():
        return
    await config_cache.load_snapshot(db)


async def _get_enabled_config(db: AsyncSession) -> tuple[set[int], set[int], set[int]]:
    await _ensure_config_snapshot(db)

    enabled_tool_ids = {item["id"] for item in config_cache.get_enabled_tools()}
    enabled_agent_ids = {item["id"] for item in config_cache.get_enabled_agents()}
    enabled_rule_ids = {item["id"] for item in config_cache.get_enabled_detection_rules()}
    return enabled_tool_ids, enabled_agent_ids, enabled_rule_ids


async def execute_query(
    db: AsyncSession,
    pipeline_uid: str,
    query: str,
    session_id: str | None = None,
) -> dict:
    """
    执行查询流水线，支持 SINGLE_AGENT / MULTI_AGENT。
    返回 dict: {answer, pipeline_type, tools_called, session_id, latency_ms}
    """
    pipeline = await _load_pipeline(db, pipeline_uid)
    enabled_tool_ids, enabled_agent_ids, enabled_rule_ids = await _get_enabled_config(db)

    # 拆分前/后置规则
    pre_rules = [r for r in pipeline.detection_rules if r.stage == "PRE" and r.id in enabled_rule_ids]
    post_rules = [r for r in pipeline.detection_rules if r.stage == "POST" and r.id in enabled_rule_ids]
    pre_rules.sort(key=lambda r: r.priority)
    post_rules.sort(key=lambda r: r.priority)

    # 前置检测（失败时抛 PreCheckRejected）
    await run_pre_detection(pre_rules, query)

    if pipeline.primary_agent and pipeline.primary_agent.id not in enabled_agent_ids:
        raise BusinessValidationError("流水线配置的 primary_agent 未启用")

    if pipeline.pipeline_type == PipelineType.MULTI_AGENT:
        from src.agents.multi_agent import run_multi_agent

        raw_sub_agent_ids: list[int] = pipeline.primary_agent.sub_agent_ids or [] if pipeline.primary_agent else []
        if raw_sub_agent_ids:
            sub_agents_q = (
                select(Agent)
                .where(Agent.id.in_(raw_sub_agent_ids))
                .options(
                    selectinload(Agent.llm_model),
                    selectinload(Agent.tools).selectinload(Tool.mcp_server),
                )
            )
            all_sub_agents = (await db.execute(sub_agents_q)).scalars().all()
        else:
            all_sub_agents = []
        enabled_sub_agents = [a for a in all_sub_agents if a.id in enabled_agent_ids]
        result = await run_multi_agent(
            pipeline,
            query,
            session_id,
            sub_agents=enabled_sub_agents,
            orchestrator=pipeline.primary_agent,
        )
    elif pipeline.pipeline_type == PipelineType.SINGLE_AGENT:
        agent = pipeline.primary_agent
        if not agent:
            raise BusinessValidationError("流水线未配置 primary_agent")

        tools = [tool for tool in agent.tools if tool.id in enabled_tool_ids]

        # 意图路由（选择工具子集）
        intent = await route_intent(query, tools)
        selected_tool_names = set(intent.selected_tools)
        effective_tools = [t for t in tools if t.name in selected_tool_names] if selected_tool_names else tools

        # 执行 Agent
        result = await run_single_agent(agent, query, effective_tools, session_id)
    else:
        raise BusinessValidationError(f"不支持的流水线类型: {pipeline.pipeline_type}")

    # 后置检测（失败时抛 PostCheckRejected）
    await run_post_detection(post_rules, result["answer"])

    return {
        "answer": result["answer"],
        "pipeline_type": pipeline.pipeline_type.value,
        "tools_called": result["tools_called"],
        "session_id": result["session_id"],
        "latency_ms": result["latency_ms"],
    }


async def execute_stream_query(
    db: AsyncSession,
    pipeline_uid: str,
    query: str,
    session_id: str | None = None,
):
    """
    流式执行查询流水线，逐事件 yield SSE 事件 dict。
    SINGLE_AGENT: 真实 token 级流式；MULTI_AGENT: 退化为批量推送。
    """
    from src.agents.single_agent import stream_single_agent

    pipeline = await _load_pipeline(db, pipeline_uid)
    enabled_tool_ids, enabled_agent_ids, enabled_rule_ids = await _get_enabled_config(db)

    pre_rules = [r for r in pipeline.detection_rules if r.stage == "PRE" and r.id in enabled_rule_ids]
    post_rules = [r for r in pipeline.detection_rules if r.stage == "POST" and r.id in enabled_rule_ids]
    pre_rules.sort(key=lambda r: r.priority)
    post_rules.sort(key=lambda r: r.priority)

    # 前置检测
    try:
        await run_pre_detection(pre_rules, query)
    except PreCheckRejected as e:
        yield {"type": "error", "code": 40301, "message": str(e)}
        return

    if pipeline.pipeline_type == PipelineType.MULTI_AGENT:
        # P3 延期：退化为批量推送
        try:
            result = await execute_query(db, pipeline_uid, query, session_id)
            yield {"type": "answer", "content": result["answer"]}
            # 不需要再全文非流式返回
            # yield {
            #     "type": "done",
            #     "answer": result["answer"],
            #     "tools_called": result["tools_called"],
            #     "latency_ms": result["latency_ms"],
            #     "session_id": result["session_id"],
            # }
        except PostCheckRejected as e:
            yield {"type": "error", "code": 40302, "message": str(e)}
        except Exception as e:
            yield {"type": "error", "code": 50000, "message": str(e)}
        return

    # SINGLE_AGENT 真实流式
    agent = pipeline.primary_agent
    if not agent:
        yield {"type": "error", "code": 50001, "message": "流水线未配置 primary_agent"}
        return
    if agent.id not in enabled_agent_ids:
        yield {"type": "error", "code": 50001, "message": "primary_agent 未启用"}
        return

    tools = [t for t in agent.tools if t.id in enabled_tool_ids]

    # 意图路由
    intent = await route_intent(query, tools)
    selected_names = set(intent.selected_tools)
    effective_tools = [t for t in tools if t.name in selected_names] if selected_names else tools

    accumulated_answer = ""
    final_event: dict | None = None

    try:
        async for event in stream_single_agent(agent, query, effective_tools, session_id):
            etype = event.get("type", "")

            if etype == "__done__":
                final_event = event
                break
            elif etype == "__error__":
                yield {"type": "error", "code": 50000, "message": event.get("message", "")}
                return
            else:
                # 转发公共事件（answer/thinking/tool_start/tool_end）
                if etype == "answer":
                    accumulated_answer += event.get("content", "")
                yield event

    except Exception as e:
        yield {"type": "error", "code": 50000, "message": f"流式执行异常：{e}"}
        return

    if final_event is None:
        yield {"type": "error", "code": 50000, "message": "Agent 未返回结果"}
        return

    # 后置检测
    try:
        await run_post_detection(post_rules, accumulated_answer)
    except PostCheckRejected as e:
        yield {"type": "error", "code": 40302, "message": str(e)}
        return

    # 不需要再全文非流式返回
    # yield {
    #     "type": "done",
    #     "answer": final_event.get("answer", accumulated_answer),
    #     "tools_called": final_event.get("tools_called", []),
    #     "latency_ms": final_event.get("latency_ms", 0),
    #     "session_id": final_event.get("session_id", ""),
    # }
