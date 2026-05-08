"""运行时上下文：持有所有内存池和缓存的单例容器。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.pool.agent_pool import AgentPool
    from src.agents.pool.mcp_pool import MCPConnectionPool
    from src.agents.pool.skill_pool import SkillPool
    from src.agents.pool.tool_pool import ToolPool
    from src.models.detection_rule import DetectionRule


@dataclass
class PipelineCacheEntry:
    """流水线配置缓存条目，运行时对话路径使用，不读取数据库。

    Attributes:
        pipeline_uid: 流水线唯一标识符（UUID 字符串）。
        pipeline_id: 流水线数据库 ID。
        pipeline_type: 流水线类型（SINGLE_AGENT / MULTI_AGENT）。
        primary_agent_id: 主 Agent ID。
        detection_rule_ids: 关联的检测规则 ID 列表。
        route_confidence_threshold: 路由置信度阈值。
        timeout_seconds: 单次对话超时秒数。
        enabled: 流水线是否启用。
    """

    pipeline_uid: str
    pipeline_id: int
    pipeline_type: str
    primary_agent_id: int
    detection_rule_ids: list[int] = field(default_factory=list)
    route_confidence_threshold: float = 0.7
    timeout_seconds: int = 30
    enabled: bool = True


@dataclass
class RuntimeContext:
    """运行时上下文单例，持有所有内存池和缓存。

    对话路径（POST /api/v1/query）完全通过此对象获取数据，
    不发起任何数据库查询。

    Attributes:
        agent_pool: Agent 实例池（含 CompiledStateGraph）。
        tool_pool: LangChain StructuredTool 缓存池。
        skill_pool: 技能缓存池。
        mcp_pool: MCP Server 长连接池。
        pipeline_cache: pipeline_uid → PipelineCacheEntry 映射。
        detection_cache: rule_id → DetectionRule 映射。
    """

    agent_pool: AgentPool
    tool_pool: ToolPool
    skill_pool: SkillPool
    mcp_pool: MCPConnectionPool
    pipeline_cache: dict[str, PipelineCacheEntry] = field(default_factory=dict)
    detection_cache: dict[int, DetectionRule] = field(default_factory=dict)

    def get_pipeline(self, pipeline_uid: str) -> PipelineCacheEntry | None:
        """按 UID 查询流水线缓存。

        Args:
            pipeline_uid: 流水线唯一标识符。

        Returns:
            对应的 PipelineCacheEntry，不存在时返回 None。
        """
        return self.pipeline_cache.get(pipeline_uid)

    def get_detection_rules(self, rule_ids: list[int]) -> list[DetectionRule]:
        """按 ID 列表获取检测规则，跳过未找到的 ID。

        Args:
            rule_ids: 检测规则 ID 列表。

        Returns:
            对应的 DetectionRule 列表。
        """
        return [self.detection_cache[rid] for rid in rule_ids if rid in self.detection_cache]

    def update_pipeline_enabled_for_agent(self, agent_id: int, enabled: bool) -> None:
        """更新指定 Agent 对应流水线的启用状态。"""
        for entry in self.pipeline_cache.values():
            if entry.primary_agent_id == agent_id:
                entry.enabled = enabled
                return

    def remove_pipeline_for_agent(self, agent_id: int) -> None:
        """从缓存中移除指定 Agent 对应的流水线。"""
        keys = [uid for uid, e in self.pipeline_cache.items() if e.primary_agent_id == agent_id]
        for key in keys:
            del self.pipeline_cache[key]
