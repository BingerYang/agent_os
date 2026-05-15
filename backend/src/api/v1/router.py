from fastapi import APIRouter

from src.api.v1 import (
    agent_detection,
    agents,
    detection_events,
    detection_rules,
    events,
    marketplace,
    mcp_servers,
    models_config,
    pipelines,
    policy_audits,
    query,
    skills,
    tools,
)

api_router = APIRouter()

api_router.include_router(mcp_servers.router, prefix="/mcp-servers", tags=["MCP Server 管理"])
api_router.include_router(models_config.router, prefix="/models", tags=["模型配置"])
api_router.include_router(models_config.router, prefix="/models-config", tags=["模型配置"])
api_router.include_router(tools.router, prefix="/tools", tags=["工具管理"])
api_router.include_router(skills.router, prefix="/skills", tags=["技能管理"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agent 管理"])
api_router.include_router(agent_detection.router, prefix="/agents", tags=["Agent 检测策略绑定"])
api_router.include_router(pipelines.router, prefix="/pipelines", tags=["流水线管理"])
api_router.include_router(detection_rules.router, prefix="/detection-rules", tags=["检测规则"])
api_router.include_router(detection_events.router, prefix="/detection-events", tags=["检测事件审计"])
api_router.include_router(policy_audits.router, prefix="/policy-config-audits", tags=["策略配置审计"])
api_router.include_router(marketplace.router, prefix="/marketplace", tags=["marketplace"])
api_router.include_router(query.router, prefix="/query", tags=["查询入口"])
api_router.include_router(events.router, prefix="", tags=["事件流"])
