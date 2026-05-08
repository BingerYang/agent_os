"""运行时加载器：DB 全量加载 + Redis Stream 热加载订阅。"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from src.core.config import get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.runtime.context import RuntimeContext

    from redis.asyncio.client import Redis

logger = logging.getLogger(__name__)


async def load_from_db(db: AsyncSession) -> RuntimeContext:
    """从数据库全量加载运行时上下文。

    启动时执行一次，加载所有启用的流水线、检测规则和已发布 Agent。
    数据库不可用时直接抛出异常，不降级（Fail Fast 原则）。

    Args:
        db: SQLAlchemy 异步会话。

    Returns:
        填充完整的 RuntimeContext 单例。

    Raises:
        Exception: 数据库连接失败或数据加载异常，均向上抛出。
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from src.agents.pool.agent_pool import AgentPool
    from src.agents.pool.mcp_pool import MCPConnectionPool
    from src.agents.pool.skill_pool import SkillPool
    from src.agents.pool.tool_pool import ToolPool
    from src.core.config import get_settings
    from src.models.agent_publish import AgentPublish
    from src.models.detection_rule import DetectionRule
    from src.models.pipeline import Pipeline
    from src.runtime.context import PipelineCacheEntry, RuntimeContext

    settings = get_settings()

    # 初始化池
    mcp_pool = MCPConnectionPool()
    tool_pool = ToolPool()
    skill_pool = SkillPool()
    agent_pool = AgentPool(max_size=settings.runtime_agent_pool_max_size)

    # 加载启用的流水线
    pipeline_cache: dict[str, PipelineCacheEntry] = {}
    try:
        result = await db.execute(
            select(Pipeline)
            .where(Pipeline.enabled == True)  # noqa: E712
            .options(selectinload(Pipeline.detection_rules))
        )
        pipelines = result.scalars().all()
    except Exception as exc:
        logger.error("loader.load_pipelines_failed error=%s", exc)
        raise

    for pl in pipelines:
        if not pl.uid or pl.primary_agent_id is None:
            continue
        pipeline_cache[pl.uid] = PipelineCacheEntry(
            pipeline_uid=pl.uid,
            pipeline_id=pl.id,
            pipeline_type=pl.pipeline_type.value,
            primary_agent_id=pl.primary_agent_id,
            detection_rule_ids=[r.id for r in (pl.detection_rules or [])],
            route_confidence_threshold=pl.route_confidence_threshold or 0.7,
            timeout_seconds=pl.timeout_seconds or 30,
            enabled=pl.enabled,
        )
    logger.info("loader.pipelines_loaded count=%d", len(pipeline_cache))

    # 加载启用的检测规则
    detection_cache: dict[int, DetectionRule] = {}
    try:
        result = await db.execute(
            select(DetectionRule).where(DetectionRule.enabled == True)  # noqa: E712
        )
        rules: list[Any] = list(result.scalars().all())
    except Exception as exc:
        logger.error("loader.load_detection_rules_failed error=%s", exc)
        raise

    for rule in rules:
        detection_cache[rule.id] = rule
    logger.info("loader.detection_rules_loaded count=%d", len(detection_cache))

    # 加载已发布 Agent（is_active=True）
    try:
        result = await db.execute(
            select(AgentPublish).where(AgentPublish.is_active == True)  # noqa: E712
        )
        publishes: list[Any] = list(result.scalars().all())
    except Exception as exc:
        logger.error("loader.load_agent_publishes_failed error=%s", exc)
        raise

    logger.info("loader.agent_publishes_found count=%d", len(publishes))

    for pub in publishes:
        try:
            snapshot: dict[str, Any] = dict(pub.config_snapshot or {})
            snapshot["version"] = pub.version

            # 先构建工具池和技能池
            await tool_pool.build_from_snapshot(snapshot.get("tools") or [], mcp_pool)
            skill_pool.build_from_snapshot(snapshot.get("skills") or [])

            # 构建 Agent 池条目
            entry = await AgentPool.build_entry(snapshot, tool_pool, mcp_pool)
            agent_pool.upsert(entry)
        except Exception as exc:
            logger.warning(
                "loader.agent_load_skipped agent_id=%s error=%s",
                pub.agent_id, exc,
            )

    logger.info("loader.agents_loaded count=%d", agent_pool.size())

    return RuntimeContext(
        agent_pool=agent_pool,
        tool_pool=tool_pool,
        skill_pool=skill_pool,
        mcp_pool=mcp_pool,
        pipeline_cache=pipeline_cache,
        detection_cache=detection_cache,
    )


async def _redis_subscriber_loop(
        context: RuntimeContext,
        stream_key: str,
) -> None:
    """Redis Stream 订阅循环（后台 Task）。

    启动时从 '$' 开始（忽略积压，DB 全量加载已覆盖）。
    正常运行时追踪 last_id，增量消费新事件。
    事件处理：按 agent_id 分组取 max publish_id，从 DB 获取最新 snapshot 后更新池。
    连接断开时使用指数退避重试（最大 60 秒）。

    Args:
        context: 运行时上下文，持有需要更新的各池。
        stream_key: Redis Stream 键名（如 "agent:publish"）。
    """

    from src.core.database import AsyncSessionLocal as async_session_factory

    retry_delay = 1.0
    last_id = "$"

    while True:
        try:
            redis_client = get_settings().load_redis_client()
            retry_delay = 1.0  # 重置退避
            logger.info("loader.redis_subscriber_connected stream=%s", stream_key)

            while True:
                results = await redis_client.xread(
                    {stream_key: last_id}, block=1000, count=100
                )
                if not results:
                    continue

                events: list[tuple[str, dict]] = results[0][1]
                last_id = events[-1][0]

                # 分离 publish 事件（按 agent_id 取 max publish_id）和立即处理事件
                latest: dict[str, str] = {}
                for _eid, fields in events:
                    action = fields.get("action", "publish")
                    aid = fields.get("agent_id", "")
                    if not aid:
                        continue

                    if action == "remove":
                        # 立即从池中移除
                        context.agent_pool.remove(int(aid))
                        context.remove_pipeline_for_agent(int(aid))
                        logger.info("loader.agent_removed agent_id=%s", aid)
                    elif action == "disable_pipeline":
                        context.update_pipeline_enabled_for_agent(int(aid), False)
                        logger.info("loader.pipeline_disabled agent_id=%s", aid)
                    elif action == "enable_pipeline":
                        context.update_pipeline_enabled_for_agent(int(aid), True)
                        logger.info("loader.pipeline_enabled agent_id=%s", aid)
                    else:
                        # action == "publish" 或无 action 字段（向后兼容）
                        pid = fields.get("publish_id", "0")
                        if aid not in latest or int(pid) > int(latest[aid]):
                            latest[aid] = pid

                # 从 DB 获取最新 snapshot 并更新池
                async with async_session_factory() as db:
                    for agent_id_str, publish_id_str in latest.items():
                        await _reload_agent(
                            db=db,
                            agent_id=int(agent_id_str),
                            publish_id=int(publish_id_str),
                            context=context,
                        )

        except asyncio.CancelledError:
            logger.info("loader.redis_subscriber_cancelled")
            break
        except Exception as exc:
            logger.error(
                "loader.redis_subscriber_error error=%s retry_in=%.1fs",
                exc, retry_delay,
            )
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60.0)


async def _reload_agent(
        db: AsyncSession,
        agent_id: int,
        publish_id: int,
        context: RuntimeContext,
) -> None:
    """从数据库重新加载指定发布版本的 Agent 并更新内存池。

    Args:
        db: 数据库会话（后台任务专用，非对话路径）。
        agent_id: 要更新的 Agent ID。
        publish_id: 新发布记录的 ID。
        context: 运行时上下文。
    """

    from sqlalchemy import select

    from src.agents.pool.agent_pool import AgentPool
    from src.models.agent_publish import AgentPublish

    try:
        result = await db.execute(
            select(AgentPublish).where(AgentPublish.id == publish_id)
        )
        pub = result.scalar_one_or_none()
        if pub is None:
            logger.warning("loader.reload_publish_not_found publish_id=%d", publish_id)
            return

        snapshot: dict[str, Any] = dict(pub.config_snapshot or {})
        snapshot["version"] = pub.version

        await context.tool_pool.build_from_snapshot(
            snapshot.get("tools") or [], context.mcp_pool
        )
        context.skill_pool.build_from_snapshot(snapshot.get("skills") or [])

        entry = await AgentPool.build_entry(snapshot, context.tool_pool, context.mcp_pool)
        context.agent_pool.upsert(entry)
        # 同步更新 pipeline_cache（热发布后新 Pipeline 路由立刻可用）
        from src.models.pipeline import Pipeline as _Pipeline
        from src.runtime.context import PipelineCacheEntry
        pipeline_result = await db.execute(
            select(_Pipeline).where(
                _Pipeline.primary_agent_id == agent_id,
                _Pipeline.enabled == True,  # noqa: E712
            )
        )
        pipeline = pipeline_result.scalar_one_or_none()
        if pipeline and pipeline.uid:
            from sqlalchemy.orm import selectinload as _sil
            det_result = await db.execute(
                select(_Pipeline)
                .where(_Pipeline.id == pipeline.id)
                .options(_sil(_Pipeline.detection_rules))
            )
            pl_with_rules = det_result.scalar_one_or_none()
            detection_rule_ids = (
                [r.id for r in pl_with_rules.detection_rules]
                if pl_with_rules
                else []
            )
            context.pipeline_cache[pipeline.uid] = PipelineCacheEntry(
                pipeline_uid=pipeline.uid,
                pipeline_id=pipeline.id,
                pipeline_type=pipeline.pipeline_type.value,
                primary_agent_id=agent_id,
                detection_rule_ids=detection_rule_ids,
                route_confidence_threshold=pipeline.route_confidence_threshold or 0.7,
                timeout_seconds=pipeline.timeout_seconds or 30,
                enabled=True,
            )
        logger.info(
            "loader.agent_reloaded agent_id=%d version=%d",
            agent_id, pub.version,
        )
    except Exception as exc:
        logger.error(
            "loader.agent_reload_failed agent_id=%d publish_id=%d error=%s",
            agent_id, publish_id, exc,
        )


def start_redis_subscriber(
        context: RuntimeContext,
        stream_key: str,
) -> asyncio.Task:
    """启动 Redis Stream 后台订阅 Task。

    Args:
        context: 运行时上下文。
        stream_key: Redis Stream 键名。

    Returns:
        asyncio.Task 实例，可在 shutdown 时调用 task.cancel()。
    """
    return asyncio.create_task(
        _redis_subscriber_loop(context, stream_key),
        name="redis_subscriber",
    )


def stop_redis_subscriber(task: asyncio.Task) -> None:
    """取消 Redis Stream 订阅 Task。

    Args:
        task: 由 start_redis_subscriber 返回的 Task 实例。
    """
    if task and not task.done():
        task.cancel()
        logger.info("loader.redis_subscriber_stopped")
