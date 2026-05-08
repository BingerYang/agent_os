"""Agent 池：缓存已编译的 CompiledStateGraph 实例，支持淘汰策略。"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.agents.pool.mcp_pool import MCPConnectionPool
    from src.agents.pool.tool_pool import ToolPool

logger = logging.getLogger(__name__)


@dataclass
class AgentEvictionEvent:
    """Agent 淘汰事件，供 on_eviction hook 使用（V2 接入告警）。

    Attributes:
        agent_id: 被淘汰的 Agent ID。
        version: 被淘汰的发布版本号。
        score: 淘汰评分（越高越优先淘汰）。
        reason: 淘汰原因描述。
    """

    agent_id: int
    version: int
    score: float
    reason: str = "pool_capacity"


@dataclass
class AgentPoolEntry:
    """Agent 池中的单个条目，持有可复用的 CompiledStateGraph。

    CompiledStateGraph 是纯 Python 可调用对象，不持有对话状态，
    可安全地跨请求并发复用（LangGraph 官方保证）。

    Attributes:
        agent_id: Agent ID。
        version: 对应的 AgentPublish.version。
        agent_type: Agent 类型（SINGLE / ORCHESTRATOR 等）。
        compiled_graph: deepagents.create_deep_agent 返回的已编译图实例。
        lc_tools: 该 Agent 使用的 LangChain StructuredTool 列表。
        system_prompt: 已渲染的系统提示词。
        llm_config: LLM 连接参数（含解密后的 api_key）。
        tool_ids: 工具 ID 列表（用于从 ToolPool 重建）。
        sub_agent_ids: ORCHESTRATOR 类型的子 Agent ID 列表。
        route_confidence_threshold: 路由置信度阈值。
        timeout_seconds: 单次对话超时秒数。
        loaded_at: 首次加载时间（淘汰评分用）。
        last_accessed_at: 最近一次被调用时间（淘汰评分用）。
        access_count: 累计调用次数。
    """

    agent_id: int
    version: int
    agent_type: str
    compiled_graph: Any  # CompiledStateGraph
    lc_tools: list[Any] = field(default_factory=list)
    system_prompt: str = ""
    llm_config: dict[str, Any] = field(default_factory=dict)
    tool_ids: list[int] = field(default_factory=list)
    sub_agent_ids: list[int] = field(default_factory=list)
    route_confidence_threshold: float = 0.7
    timeout_seconds: int = 30
    loaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = 0


class AgentPool:
    """运行时 Agent 池，持有已编译的 graph 实例，支持容量上限和淘汰策略。

    淘汰评分公式：score = 0.3 × age_hours + 0.7 × idle_hours
    得分最高者（最老且最长时间未访问）优先淘汰。

    Args:
        max_size: 池最大容量，0 表示不限制。
    """

    def __init__(self, max_size: int = 0) -> None:
        self._pool: dict[int, AgentPoolEntry] = {}
        self._max_size = max_size

    @classmethod
    async def build_entry(
        cls,
        publish_snapshot: dict[str, Any],
        tool_pool: ToolPool,
        mcp_pool: MCPConnectionPool,
    ) -> AgentPoolEntry:
        """从 config_snapshot 构建 AgentPoolEntry。

        调用 deepagents.create_deep_agent 并编译图实例；
        工具列表从 ToolPool 获取（避免重复构建）。

        Args:
            publish_snapshot: AgentPublish.config_snapshot 字典。
            tool_pool: 运行时工具池（工具已提前构建）。
            mcp_pool: MCP 连接池（工具构建失败时的回退路径使用）。

        Returns:
            已填充 compiled_graph 的 AgentPoolEntry。

        Raises:
            ValueError: Agent 未配置 LLM 模型时抛出。
        """
        from deepagents import create_deep_agent
        from langchain_openai import ChatOpenAI

        from src.services.llm_model_service import decrypt_api_key

        llm_cfg = publish_snapshot.get("llm_model") or {}
        if not llm_cfg:
            raise ValueError(f"Agent {publish_snapshot.get('agent_id')} 未配置 LLM 模型")

        tool_ids: list[int] = [t["id"] for t in (publish_snapshot.get("tools") or [])]
        lc_tools = tool_pool.get_lc_tools(tool_ids)

        api_key = decrypt_api_key(llm_cfg.get("api_key_encrypted", ""))
        llm = ChatOpenAI(
            model=llm_cfg["model_id"],
            api_key=api_key,  # type: ignore[arg-type]
            base_url=llm_cfg.get("endpoint_url") or None,
            temperature=publish_snapshot.get("temperature", 0.7),
            max_completion_tokens=publish_snapshot.get("max_tokens", 2048),
        )

        system_prompt = publish_snapshot.get("system_prompt") or "你是一个智能助手，请根据用户查询提供帮助。"
        compiled_graph = create_deep_agent(
            model=llm,
            tools=lc_tools,
            system_prompt=system_prompt,
        )

        return AgentPoolEntry(
            agent_id=int(publish_snapshot["agent_id"]),
            version=int(publish_snapshot.get("version", 1)),
            agent_type=str(publish_snapshot.get("agent_type", "SINGLE")),
            compiled_graph=compiled_graph,
            lc_tools=lc_tools,
            system_prompt=system_prompt,
            llm_config={
                "model_id": llm_cfg["model_id"],
                "endpoint_url": llm_cfg.get("endpoint_url"),
            },
            tool_ids=tool_ids,
            sub_agent_ids=[int(i) for i in (publish_snapshot.get("sub_agent_ids") or [])],
            route_confidence_threshold=float(publish_snapshot.get("route_confidence_threshold", 0.7)),
            timeout_seconds=int(publish_snapshot.get("timeout_seconds", 30)),
        )

    def get(self, agent_id: int) -> AgentPoolEntry | None:
        """获取 Agent 条目，同时更新访问统计。

        Args:
            agent_id: Agent ID。

        Returns:
            对应的 AgentPoolEntry，不存在时返回 None。
        """
        entry = self._pool.get(agent_id)
        if entry is not None:
            entry.last_accessed_at = datetime.now(UTC)
            entry.access_count += 1
        return entry

    def upsert(self, entry: AgentPoolEntry) -> None:
        """插入或更新 Agent 条目；若池已满则先淘汰一个条目。

        Args:
            entry: 要插入或更新的 AgentPoolEntry。
        """
        if (
            self._max_size > 0
            and entry.agent_id not in self._pool
            and len(self._pool) >= self._max_size
        ):
            self.evict_one()
        self._pool[entry.agent_id] = entry
        logger.info(
            "agent_pool.upsert agent_id=%d version=%d pool_size=%d",
            entry.agent_id, entry.version, len(self._pool),
        )

    def evict_one(self) -> int:
        """按评分淘汰得分最高的条目，返回被淘汰的 agent_id。

        评分公式：score = 0.3 × age_hours + 0.7 × idle_hours
        得分越高 → 越老且越长时间未访问 → 优先淘汰。

        Returns:
            被淘汰条目的 agent_id。
        """
        victim_id = max(self._pool, key=lambda k: self._eviction_score(self._pool[k]))
        entry = self._pool.pop(victim_id)
        score = self._eviction_score(entry)
        logger.info(
            "agent_pool.evict agent_id=%d version=%d score=%.3f",
            victim_id, entry.version, score,
        )
        import asyncio
        try:
            asyncio.create_task(  # noqa: RUF006
                self.on_eviction(AgentEvictionEvent(
                    agent_id=victim_id,
                    version=entry.version,
                    score=score,
                ))
            )
        except RuntimeError:
            pass  # 无运行中的事件循环（如同步测试环境），跳过异步通知
        return victim_id

    def remove(self, agent_id: int) -> bool:
        """从池中移除指定 Agent。"""
        return bool(self._pool.pop(agent_id, None))

    async def on_eviction(self, event: AgentEvictionEvent) -> None:
        """淘汰事件 hook，V1 为空实现，V2 可接入告警通知。

        Args:
            event: 淘汰事件详情。
        """

    def size(self) -> int:
        """返回当前池中的 Agent 数量。"""
        return len(self._pool)

    @staticmethod
    def _eviction_score(entry: AgentPoolEntry) -> float:
        """计算淘汰评分（越高越优先淘汰）。"""
        now = datetime.now(UTC)
        age_h = (now - entry.loaded_at).total_seconds() / 3600
        idle_h = (now - entry.last_accessed_at).total_seconds() / 3600
        return 0.3 * age_h + 0.7 * idle_h
