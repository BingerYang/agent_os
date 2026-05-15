from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import ApiResponse, PageResult
from src.services.detection_service import DetectionService

router = APIRouter()
_svc = DetectionService()


class DetectionRuleCreate(BaseModel):
    name: str
    stage: str
    rule_type: str
    strategy_type: str = "content_filter"
    action_type: str = "block"
    max_retry_count: int = 3
    rule_content: dict[str, Any]
    reject_message: str | None = None
    priority: int = 100


class DetectionRuleUpdate(BaseModel):
    name: str | None = None
    stage: str | None = None
    rule_type: str | None = None
    strategy_type: str | None = None
    action_type: str | None = None
    max_retry_count: int | None = None
    rule_content: dict[str, Any] | None = None
    reject_message: str | None = None
    priority: int | None = None


class ToggleBody(BaseModel):
    enabled: bool


def _to_dict(obj: Any) -> dict[str, Any]:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


_STRATEGY_META = [
    {
        "value": "rate_limit",
        "label": "频率限制",
        "code": "P-01",
        "stage": "PRE",
        "description": "限制单位时间内的请求频次，防止刷接口和突发流量冲击。",
        "config_schema": [
            {"field": "window_seconds", "label": "统计窗口（秒）", "type": "integer", "default": 60},
            {"field": "max_requests", "label": "最大请求数", "type": "integer", "default": 100},
            {
                "field": "key_by",
                "label": "限流维度",
                "type": "select",
                "options": ["user", "ip", "agent"],
                "default": "user",
            },
            {"field": "burst_limit", "label": "突发阈值", "type": "integer", "default": 20},
        ],
    },
    {
        "value": "identity_verify",
        "label": "身份校验",
        "code": "P-02",
        "stage": "PRE",
        "description": "校验请求身份、令牌类型和匿名访问策略。",
        "config_schema": [
            {
                "field": "require_token_types",
                "label": "要求令牌类型",
                "type": "multiselect",
                "options": ["bearer", "api_key"],
                "default": ["bearer"],
            },
            {"field": "check_expiry", "label": "检查过期时间", "type": "boolean", "default": True},
            {"field": "allow_anonymous", "label": "允许匿名访问", "type": "boolean", "default": False},
        ],
    },
    {
        "value": "content_filter",
        "label": "内容过滤",
        "code": "P-03",
        "stage": "PRE",
        "description": "基于分类、关键词和模式过滤高风险输入内容。",
        "config_schema": [
            {
                "field": "sub_types",
                "label": "子类型",
                "type": "multiselect",
                "options": ["political", "pornography", "violence", "attack"],
                "default": ["political", "pornography", "violence", "attack"],
            },
            {"field": "keywords", "label": "关键词", "type": "stringlist", "default": []},
            {"field": "patterns", "label": "匹配模式", "type": "stringlist", "default": []},
            {"field": "use_llm_judge", "label": "启用 LLM 判定", "type": "boolean", "default": False},
            {"field": "llm_threshold", "label": "LLM 阈值", "type": "number", "default": 0.8},
        ],
    },
    {
        "value": "prompt_injection",
        "label": "提示词注入检测",
        "code": "P-04",
        "stage": "PRE",
        "description": "识别越权指令、系统提示泄露和注入攻击。",
        "config_schema": [
            {
                "field": "patterns",
                "label": "匹配模式",
                "type": "stringlist",
                "default": ["ignore previous instructions"],
            },
            {
                "field": "injection_keywords",
                "label": "注入关键词",
                "type": "stringlist",
                "default": ["system:", "###"],
            },
            {"field": "use_llm_judge", "label": "启用 LLM 判定", "type": "boolean", "default": True},
        ],
    },
    {
        "value": "pii_desensitize",
        "label": "PII 脱敏",
        "code": "P-05",
        "stage": "PRE",
        "description": "识别并脱敏输入中的个人敏感信息。",
        "config_schema": [
            {
                "field": "pii_types",
                "label": "PII 类型",
                "type": "multiselect",
                "options": ["phone", "idcard", "email", "bankcard", "name"],
                "default": ["phone", "idcard", "email"],
            },
            {"field": "mask_pattern", "label": "脱敏样式", "type": "string", "default": "***"},
            {"field": "partial_mask", "label": "部分脱敏", "type": "boolean", "default": True},
        ],
    },
    {
        "value": "intent_compliance",
        "label": "意图合规",
        "code": "P-06",
        "stage": "PRE",
        "description": "判断用户意图是否在允许范围内，并拦截违规请求。",
        "config_schema": [
            {"field": "allowed_intents", "label": "允许意图", "type": "stringlist", "default": []},
            {"field": "deny_intents", "label": "禁止意图", "type": "stringlist", "default": []},
            {
                "field": "system_prompt",
                "label": "系统提示词",
                "type": "textarea",
                "default": "判断用户意图是否在以下允许范围内...",
            },
            {"field": "confidence_threshold", "label": "置信度阈值", "type": "number", "default": 0.7},
        ],
    },
    {
        "value": "rbac_check",
        "label": "RBAC 权限校验",
        "code": "P-07",
        "stage": "PRE",
        "description": "根据角色和权限控制访问，支持禁用和降级角色。",
        "config_schema": [
            {"field": "required_roles", "label": "要求角色", "type": "stringlist", "default": ["user"]},
            {"field": "required_permissions", "label": "要求权限", "type": "stringlist", "default": []},
            {"field": "deny_roles", "label": "禁止角色", "type": "stringlist", "default": ["banned"]},
            {"field": "degrade_roles", "label": "降级角色", "type": "stringlist", "default": []},
        ],
    },
    {
        "value": "business_rule",
        "label": "业务规则",
        "code": "P-08",
        "stage": "PRE",
        "description": "执行自定义业务规则编排，支持复合条件判断。",
        "config_schema": [
            {"field": "rules", "label": "规则列表", "type": "rulelist", "default": []},
        ],
    },
    {
        "value": "privacy_leak",
        "label": "隐私泄露检测",
        "code": "A-01",
        "stage": "POST",
        "description": "检查输出结果中的隐私信息泄露并进行脱敏处理。",
        "config_schema": [
            {
                "field": "pii_types",
                "label": "PII 类型",
                "type": "multiselect",
                "options": ["phone", "idcard", "email", "bankcard", "name"],
                "default": ["phone", "idcard", "email"],
            },
            {"field": "mask_pattern", "label": "脱敏样式", "type": "string", "default": "***"},
            {"field": "partial_mask", "label": "部分脱敏", "type": "boolean", "default": True},
        ],
    },
    {
        "value": "result_validation",
        "label": "结果校验",
        "code": "A-02",
        "stage": "POST",
        "description": "对模型输出做结构、字段和正则校验，并支持失败重试。",
        "config_schema": [
            {"field": "field_rules", "label": "字段规则", "type": "fieldruleslist", "default": []},
            {"field": "regex_checks", "label": "正则检查", "type": "stringlist", "default": []},
            {"field": "retry_count", "label": "重试次数", "type": "integer", "default": 2},
            {
                "field": "fallback_message",
                "label": "失败提示语",
                "type": "string",
                "default": "结果校验失败，请重试",
            },
        ],
    },
    {
        "value": "human_approval",
        "label": "人工审批",
        "code": "A-03",
        "stage": "POST",
        "description": "将高风险结果转交人工审批，并设置超时和回退策略。",
        "config_schema": [
            {"field": "timeout_seconds", "label": "超时时间（秒）", "type": "integer", "default": 300},
            {
                "field": "fallback_action",
                "label": "超时回退动作",
                "type": "select",
                "options": ["block", "log_only", "alert"],
                "default": "block",
            },
            {
                "field": "approver_roles",
                "label": "审批角色",
                "type": "stringlist",
                "default": ["approver"],
            },
            {
                "field": "notify_channel",
                "label": "通知渠道",
                "type": "select",
                "options": ["in_app"],
                "default": "in_app",
            },
        ],
    },
]


_ACTION_META = [
    {"value": "block", "label": "拦截"},
    {"value": "rewrite", "label": "改写"},
    {"value": "log_review", "label": "记录Review（可继续）"},
    {"value": "retry", "label": "重试"},
    {"value": "log_only", "label": "记录（仅记录）"},
    {"value": "degrade", "label": "降级"},
    {"value": "escalate", "label": "转人工"},
    {"value": "alert", "label": "告警"},
]


@router.get("/meta")
async def get_meta() -> Any:
    return ApiResponse.ok({"strategy_types": _STRATEGY_META, "action_types": _ACTION_META})


@router.get("")
async def list_rules(
    stage: str | None = None,
    rule_type: str | None = None,
    strategy_type: str | None = None,
    enabled: bool | None = None,
    keyword: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> Any:
    items, total = await _svc.list(
        db,
        stage=stage,
        rule_type=rule_type,
        strategy_type=strategy_type,
        enabled=enabled,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse.ok(
        PageResult(items=[_to_dict(i) for i in items], total=total, page=page, page_size=page_size)
    )


@router.post("")
async def create_rule(body: DetectionRuleCreate, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.create(db, body.model_dump())
    return ApiResponse.ok(_to_dict(obj))


@router.get("/{rule_id}")
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.get(db, rule_id)
    return ApiResponse.ok(_to_dict(obj))


@router.put("/{rule_id}")
async def update_rule(rule_id: int, body: DetectionRuleUpdate, db: AsyncSession = Depends(get_db)) -> Any:
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    obj = await _svc.update(db, rule_id, data)
    return ApiResponse.ok(_to_dict(obj))


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    await _svc.delete(db, rule_id)
    return ApiResponse.ok(None, message="删除成功")


@router.patch("/{rule_id}/toggle")
async def toggle_rule(rule_id: int, body: ToggleBody, db: AsyncSession = Depends(get_db)) -> Any:
    obj = await _svc.toggle(db, rule_id, body.enabled)
    return ApiResponse.ok(_to_dict(obj))
