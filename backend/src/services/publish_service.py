"""Agent 发布服务：生成 config_snapshot、写库、推送 Redis Stream。"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from redis.asyncio.client import Redis


@dataclass
class PublishResult:
    """Agent 发布操作结果。

    Attributes:
        publish_id: 新创建的 AgentPublish 记录 ID。
        agent_id: 被发布的 Agent ID。
        version: 本次发布版本号。
        redis_notified: 是否成功推送 Redis Stream 事件。
    """

    publish_id: int
    agent_id: int
    version: int
    redis_notified: bool

    def to_dict(self) -> dict[str, Any]:
        """转为字典供 JSON 序列化。"""
        return {
            "publish_id": self.publish_id,
            "agent_id": self.agent_id,
            "version": self.version,
            "redis_notified": self.redis_notified,
        }


async def publish_agent(
        db: AsyncSession,
        agent_id: int,
        published_by: str | None = None,
) -> PublishResult:
    """发布指定 Agent：生成快照、写 AgentPublish 表、通知 Redis Stream。

    操作步骤：
    1. 全量加载 Agent 及关联关系（LLM、Tools + MCP Server、Skills）。
    2. 序列化为 config_snapshot。
    3. 确定新版本号（MAX(existing) + 1，首次为 1）。
    4. 将同一 agent_id 的旧记录 is_active 置为 False。
    5. 创建新的 AgentPublish（is_active=True）。
    6. 更新 Agent.published_version 和 last_published_at。
    7. 向 Redis Stream 推送发布事件（失败不回滚）。

    Args:
        db: SQLAlchemy 异步会话。
        agent_id: 要发布的 Agent ID。
        published_by: 操作者标识（可选）。

    Returns:
        PublishResult，包含 publish_id、version、redis_notified 字段。

    Raises:
        ResourceNotFound: Agent 不存在时抛出。
        ValueError: Agent 未配置 LLM 模型时抛出。
    """
    from sqlalchemy import update as _update

    from src.core.config import get_settings
    from src.core.exceptions import ResourceNotFound
    from src.models.agent import Agent
    from src.models.agent_publish import AgentPublish
    from src.models.skill import Skill
    from src.models.tool import Tool

    settings = get_settings()

    # 1. 全量加载 Agent
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(
            selectinload(Agent.llm_model),
            selectinload(Agent.tools).selectinload(Tool.mcp_server),
            selectinload(Agent.skills).selectinload(Skill.tools),
        )
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise ResourceNotFound(f"Agent {agent_id} 不存在")
    if agent.llm_model is None:
        raise ValueError(f"Agent {agent_id} 未配置 LLM 模型，无法发布")

    # 2. 序列化 config_snapshot
    snapshot = _build_snapshot(agent)

    # 3. 确定版本号
    version_result = await db.execute(
        select(AgentPublish.version)
        .where(AgentPublish.agent_id == agent_id)
        .order_by(AgentPublish.version.desc())
        .limit(1)
    )
    last_version = version_result.scalar_one_or_none()
    new_version = (last_version or 0) + 1
    snapshot["version"] = new_version

    # 4. 旧记录 is_active → False
    await db.execute(
        _update(AgentPublish)
        .where(AgentPublish.agent_id == agent_id, AgentPublish.is_active == True)  # noqa: E712
        .values(is_active=False, updated_at=datetime.now(UTC))
    )

    # 5. 创建新 AgentPublish
    now = datetime.now(UTC)
    pub = AgentPublish(
        agent_id=agent_id,
        version=new_version,
        config_snapshot=snapshot,
        is_active=True,
        published_at=now,
        published_by=published_by,
    )
    db.add(pub)
    await db.flush()  # 获取 pub.id

    # 6. 更新 Agent 发布状态
    await db.execute(
        _update(Agent)
        .where(Agent.id == agent_id)
        .values(published_version=new_version, last_published_at=now)
    )
    await db.commit()

    logger.info(
        "publish_service.published agent_id=%d version=%d publish_id=%d",
        agent_id, new_version, pub.id,
    )

    # 7. 推送 Redis Stream（失败不回滚）
    redis_notified = await _push_redis_event(
        redis_client=settings.load_redis_client(),
        stream_key=settings.redis_stream_key,
        publish_id=pub.id,
        agent_id=agent_id,
        version=new_version,
    )

    return PublishResult(
        publish_id=pub.id,
        agent_id=agent_id,
        version=new_version,
        redis_notified=redis_notified,
    )


def _build_snapshot(agent: Any) -> dict[str, Any]:
    """将 Agent ORM 对象序列化为 config_snapshot 字典。

    Args:
        agent: 已加载所有关联关系的 Agent ORM 实例。

    Returns:
        config_snapshot 字典，结构见 data-model.md。
    """
    llm = agent.llm_model
    llm_data: dict[str, Any] = {
        "id": llm.id,
        "model_id": llm.model_id,
        "endpoint_url": llm.endpoint_url,
        "api_key_encrypted": llm.api_key,  # 已加密存储，原样快照
    }

    tools_data: list[dict[str, Any]] = []
    for tool in (agent.tools or []):
        tool_entry: dict[str, Any] = {
            "id": tool.id,
            "name": tool.name,
            "display_name": tool.display_name,
            "description": tool.description,
            "protocol": tool.protocol.value if hasattr(tool.protocol, "value") else str(tool.protocol),
            "endpoint_url": tool.endpoint_url,
            "mcp_tool_name": tool.mcp_tool_name,
            "auth_type": tool.auth_type.value if hasattr(tool.auth_type, "value") else str(tool.auth_type),
            "auth_config": tool.auth_config or {},
        }
        if tool.mcp_server:
            srv = tool.mcp_server
            tool_entry["mcp_server"] = {
                "id": srv.id,
                "endpoint_url": srv.endpoint_url,
                "auth_type": srv.auth_type.value if hasattr(srv.auth_type, "value") else str(srv.auth_type),
                "auth_config": srv.auth_config or {},
                "headers": _build_mcp_headers(srv),
            }
        tools_data.append(tool_entry)

    skills_data: list[dict[str, Any]] = []
    for skill in (agent.skills or []):
        skills_data.append({
            "id": skill.id,
            "name": skill.name,
            "description": skill.description or "",
            "tool_ids": [t.id for t in (skill.tools or [])],
        })

    return {
        "agent_id": agent.id,
        "name": agent.name,
        "agent_type": agent.agent_type.value if hasattr(agent.agent_type, "value") else str(agent.agent_type),
        "system_prompt": agent.system_prompt or "",
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
        "llm_model": llm_data,
        "tools": tools_data,
        "skills": skills_data,
        "sub_agent_ids": list(agent.sub_agent_ids or []),
        "route_confidence_threshold": agent.routing_threshold or 0.7,
        "timeout_seconds": 30,
    }


def _build_mcp_headers(srv: Any) -> dict[str, str]:
    """从 MCPServer 的 auth 配置构建 HTTP 请求头。

    Args:
        srv: MCPServer ORM 实例。

    Returns:
        认证请求头字典。
    """
    import base64

    auth = srv.auth_config or {}
    auth_type = srv.auth_type.value if hasattr(srv.auth_type, "value") else str(srv.auth_type)

    if auth_type == "BEARER_TOKEN":
        return {"Authorization": f"Bearer {auth.get('token', '')}"}
    if auth_type == "API_KEY" and auth.get("key_location", "header") == "header":
        return {auth.get("key_name", "X-API-Key"): auth.get("key_value", "")}
    if auth_type == "BASIC_AUTH":
        creds = f"{auth.get('username', '')}:{auth.get('password', '')}"
        return {"Authorization": f"Basic {base64.b64encode(creds.encode()).decode()}"}
    return {}


async def _push_redis_event(
        redis_client: Redis,
        stream_key: str,
        publish_id: int,
        agent_id: int,
        version: int,
) -> bool:
    """向 Redis Stream 推送发布事件。

    Args:
        redis_client: Redis client。
        stream_key: Stream 键名。
        publish_id: AgentPublish.id。
        agent_id: Agent ID。
        version: 发布版本号。

    Returns:
        True 表示推送成功，False 表示失败（不影响主流程）。
    """
    try:

        await redis_client.xadd(
            stream_key,
            {
                "publish_id": str(publish_id),
                "agent_id": str(agent_id),
                "version": str(version),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        await redis_client.aclose()
        logger.info(
            "publish_service.redis_notified stream=%s publish_id=%d",
            stream_key, publish_id,
        )
        return True
    except Exception as exc:
        logger.warning(
            "publish_service.redis_notify_failed error=%s (non-fatal)",
            exc,
        )
        return False
