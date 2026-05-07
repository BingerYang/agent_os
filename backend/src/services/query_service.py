"""查询服务（T028）— 运行时版本，零数据库读取。

所有数据来自 RuntimeContext 内存池，对话路径中不发起任何 DB 查询。
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from src.agents.detection import run_post_detection, run_pre_detection
from src.core.exceptions import (
    PostCheckRejected,
    PreCheckRejected,
    ResourceNotFound,
)

if TYPE_CHECKING:
    from src.runtime.context import RuntimeContext

logger = logging.getLogger(__name__)


def _build_agent_context(
    context: RuntimeContext,
    pipeline_uid: str,
    query: str,
    session_id: str | None,
) -> tuple[Any, Any, list[Any], list[Any]]:
    """从 RuntimeContext 中取出流水线配置和前/后置检测规则。

    Returns:
        (pipeline_cfg, agent_context, pre_rules, post_rules)

    Raises:
        ResourceNotFound: 流水线不存在或未启用。
    """
    from src.agents.base import AgentContext

    pipeline_cfg = context.get_pipeline(pipeline_uid)
    if not pipeline_cfg or not pipeline_cfg.enabled:
        raise ResourceNotFound(f"流水线 {pipeline_uid} 不存在或未启用")

    detection_rules = context.get_detection_rules(pipeline_cfg.detection_rule_ids)
    pre_rules = sorted([r for r in detection_rules if r.stage == "PRE"], key=lambda r: r.priority)
    post_rules = sorted([r for r in detection_rules if r.stage == "POST"], key=lambda r: r.priority)

    sid = session_id or f"sess_{uuid.uuid4().hex[:8]}"
    agent_ctx = AgentContext(
        query=query,
        session_id=sid,
        pipeline_config=pipeline_cfg,
        agent_pool=context.agent_pool,
        tool_pool=context.tool_pool,
        mcp_pool=context.mcp_pool,
    )
    return pipeline_cfg, agent_ctx, pre_rules, post_rules


async def execute_query(
    context: RuntimeContext,
    pipeline_uid: str,
    query: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """执行查询流水线（非流式），支持 SINGLE_AGENT / MULTI_AGENT。

    Returns:
        {answer, pipeline_type, tools_called, session_id, latency_ms}

    Raises:
        ResourceNotFound: 流水线不存在。
        PreCheckRejected: 前置检测命中。
        PostCheckRejected: 后置检测命中。
        BusinessValidationError: Agent 未加载等业务异常。
    """
    pipeline_cfg, agent_ctx, pre_rules, post_rules = _build_agent_context(
        context, pipeline_uid, query, session_id
    )

    await run_pre_detection(pre_rules, query)

    if pipeline_cfg.pipeline_type == "MULTI_AGENT":
        from src.agents.multi_agent import MultiAgentNode
        node: Any = MultiAgentNode()
    else:
        from src.agents.single_agent import SingleAgentNode
        node = SingleAgentNode()

    result = await node.execute(agent_ctx)

    await run_post_detection(post_rules, result.answer)

    return result.to_dict()


async def execute_stream_query(
    context: RuntimeContext,
    pipeline_uid: str,
    query: str,
    session_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """流式执行查询流水线，逐事件 yield SSE 事件 dict。

    SINGLE_AGENT 和单路由 MULTI_AGENT 支持真实 token 级流式；
    多路由 MULTI_AGENT 退化为批量推送最终答案。
    """
    try:
        pipeline_cfg, agent_ctx, pre_rules, post_rules = _build_agent_context(
            context, pipeline_uid, query, session_id
        )
    except ResourceNotFound as e:
        yield {"type": "error", "code": 40401, "message": str(e)}
        return

    try:
        await run_pre_detection(pre_rules, query)
    except PreCheckRejected as e:
        yield {"type": "error", "code": 40301, "message": str(e)}
        return

    if pipeline_cfg.pipeline_type == "MULTI_AGENT":
        from src.agents.multi_agent import MultiAgentNode
        node: Any = MultiAgentNode()
    else:
        from src.agents.single_agent import SingleAgentNode
        node = SingleAgentNode()

    accumulated_answer = ""
    final_event: dict | None = None

    try:
        async for stream_event in node.stream(agent_ctx):
            event_dict = stream_event.to_dict()
            etype = event_dict.get("type", "")

            if etype == "__done__":
                final_event = event_dict
                break
            if etype == "__error__":
                yield {"type": "error", "code": 50000, "message": event_dict.get("message", "")}
                return

            if etype == "answer":
                accumulated_answer += event_dict.get("content", "")
            yield event_dict

    except Exception as e:
        yield {"type": "error", "code": 50000, "message": f"流式执行异常：{e}"}
        return

    if final_event is None:
        yield {"type": "error", "code": 50000, "message": "Agent 未返回结果"}
        return

    try:
        await run_post_detection(post_rules, accumulated_answer)
    except PostCheckRejected as e:
        yield {"type": "error", "code": 40302, "message": str(e)}
        return
