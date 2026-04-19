"""
查询服务（T036 / T046）
支持单 Agent / 多 Agent 流水线编排：
  加载 Pipeline 配置 → PreDetection → Pipeline Dispatch → PostDetection → 构造响应
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import BusinessValidationError, ResourceNotFound
from src.models.pipeline import Pipeline, PipelineType
from src.models.agent import Agent
from src.agents.detection import run_pre_detection, run_post_detection
from src.agents.intent_router import route_intent
from src.agents.single_agent import run_single_agent
from src.services.config_cache import config_cache


async def _load_pipeline(db: AsyncSession, pipeline_id: int) -> Pipeline:
    q = (
        select(Pipeline)
        .where(Pipeline.id == pipeline_id, Pipeline.enabled == True)
        .options(
            selectinload(Pipeline.primary_agent).selectinload(Agent.tools),
            selectinload(Pipeline.primary_agent).selectinload(Agent.skills),
            selectinload(Pipeline.primary_agent).selectinload(Agent.llm_model),
            selectinload(Pipeline.sub_agents).selectinload(Agent.llm_model),
            selectinload(Pipeline.sub_agents).selectinload(Agent.tools),
            selectinload(Pipeline.detection_rules),
        )
    )
    pipeline = (await db.execute(q)).scalar_one_or_none()
    if not pipeline:
        raise ResourceNotFound(f"流水线 {pipeline_id} 不存在或未启用")
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
    pipeline_id: int,
    query: str,
    session_id: str | None = None,
) -> dict:
    """
    执行查询流水线，支持 SINGLE_AGENT / MULTI_AGENT。
    返回 dict: {answer, pipeline_type, tools_called, session_id, latency_ms}
    """
    pipeline = await _load_pipeline(db, pipeline_id)
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

        enabled_sub_agents = [agent for agent in pipeline.sub_agents if agent.id in enabled_agent_ids]
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
