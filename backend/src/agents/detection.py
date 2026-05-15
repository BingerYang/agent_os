"""
检测策略执行引擎 — 前后置检测。
支持 11 种策略类型通过 STRATEGY_REGISTRY 分发，保留原有 keyword/LLM 兜底逻辑。
"""
from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from src.core.exceptions import PostCheckRejected, PreCheckRejected
from src.models.detection_rule import DetectionRule, RuleType

logger = logging.getLogger(__name__)

# ── PII patterns ──────────────────────────────────────────────────────────────
_PII_PATTERNS: dict[str, tuple[str, str]] = {
    "phone": (r"1[3-9]\d{9}", "***"),
    "idcard": (r"\d{17}[\dXx]", "***"),
    "email": (r"[\w.+-]+@[\w-]+\.[\w.]+", "***@***.***"),
    "bankcard": (r"\b\d{16,19}\b", "****"),
    "name": (r"[一-龥]{2,4}(?:先生|女士|同学|老师)", "**"),
}

# ── Prompt injection patterns ─────────────────────────────────────────────────
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+(?:dan|jailbroken|unrestricted)",
    r"system\s*[:：]\s*ignore",
    r"<\s*/?system\s*>",
    r"\[\s*INST\s*\].*override",
]

# ── In-memory fallback rate limit counter (process-local) ─────────────────────
_rate_windows: dict[str, list[float]] = defaultdict(list)


@dataclass
class StrategyResult:
    hit: bool
    rewritten_text: str | None = None
    hit_detail: dict[str, Any] = field(default_factory=dict)


StrategyFunc = Callable[[str, dict[str, Any]], Awaitable[StrategyResult]]


# ── Strategy implementations ──────────────────────────────────────────────────

async def _check_rate_limit(text: str, config: dict[str, Any], **kw: Any) -> StrategyResult:
    """P-01 限流防刷：Redis 滑动窗口，降级到内存计数。"""
    window = int(config.get("window_seconds", 60))
    max_req = int(config.get("max_requests", 100))
    key_by = config.get("key_by", "agent")
    key = kw.get("key_by_value") or f"default:{key_by}"
    redis_key = f"rl:{key}"

    try:
        from src.core.config import settings
        r = settings.load_redis_client()
        now = int(time.time())
        pipe = r.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - window)
        pipe.zadd(redis_key, {f"{now * 1000}_{id(text) % 1000}": now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, window + 1)
        results = await pipe.execute()
        count = results[2]
        if count > max_req:
            return StrategyResult(
                hit=True,
                hit_detail={"count": count, "max_requests": max_req, "window_seconds": window},
            )
        return StrategyResult(hit=False)
    except Exception:
        now_mono = time.monotonic()
        _rate_windows[redis_key] = [t for t in _rate_windows[redis_key] if now_mono - t < window]
        _rate_windows[redis_key].append(now_mono)
        count = len(_rate_windows[redis_key])
        if count > max_req:
            return StrategyResult(hit=True, hit_detail={"count": count, "max_requests": max_req})
        return StrategyResult(hit=False)


async def _check_identity(text: str, config: dict[str, Any], **kw: Any) -> StrategyResult:
    """P-02 身份校验：检查调用上下文令牌类型。"""
    auth_context = kw.get("auth_context") or {}
    require_types = config.get("require_token_types", [])
    token_type = auth_context.get("token_type")
    if require_types and token_type not in require_types:
        return StrategyResult(
            hit=True, hit_detail={"require_token_types": require_types, "got": token_type}
        )
    if config.get("check_expiry") and auth_context.get("expired"):
        return StrategyResult(hit=True, hit_detail={"reason": "token_expired"})
    return StrategyResult(hit=False)


async def _check_content_filter(text: str, config: dict[str, Any], **kw: Any) -> StrategyResult:
    """P-03 违规内容拦截：关键词 + 可选 LLM judge。"""
    for kw_item in config.get("keywords", []):
        if kw_item in text:
            return StrategyResult(hit=True, hit_detail={"matched_keyword": kw_item})
    for pattern in config.get("patterns", []):
        if re.search(pattern, text):
            return StrategyResult(hit=True, hit_detail={"matched_pattern": pattern})
    return StrategyResult(hit=False)


async def _check_prompt_injection(text: str, config: dict[str, Any], **kw: Any) -> StrategyResult:
    """P-04 Prompt 注入防护：内置模式 + 自定义关键词。"""
    patterns = list(config.get("patterns", [])) + _INJECTION_PATTERNS
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return StrategyResult(hit=True, hit_detail={"matched_pattern": pattern})
    for inj_kw in config.get("injection_keywords", []):
        if inj_kw.lower() in text.lower():
            return StrategyResult(hit=True, hit_detail={"matched_keyword": inj_kw})
    return StrategyResult(hit=False)


async def _desensitize_pii(text: str, config: dict[str, Any], **kw: Any) -> StrategyResult:
    """P-05 / A-01 PII 脱敏：正则替换，返回脱敏文本。"""
    pii_types = config.get("pii_types", list(_PII_PATTERNS.keys()))
    rewritten = text
    replaced_types: list[str] = []
    mask_overrides = config.get("mask_pattern", {})
    for pii_type in pii_types:
        if pii_type not in _PII_PATTERNS:
            continue
        default_pattern, default_mask = _PII_PATTERNS[pii_type]
        mask = mask_overrides.get(pii_type, default_mask)
        new_text, n = re.subn(default_pattern, mask, rewritten)
        if n > 0:
            replaced_types.append(pii_type)
            rewritten = new_text
    if replaced_types:
        return StrategyResult(
            hit=True, rewritten_text=rewritten, hit_detail={"desensitized_types": replaced_types}
        )
    return StrategyResult(hit=False)


async def _check_intent_compliance(text: str, config: dict[str, Any], **kw: Any) -> StrategyResult:
    """P-06 意图 & 业务范围合规：LLM judge（无 LLM 时 pass）。"""
    llm_model = kw.get("llm_model")
    if llm_model is None:
        return StrategyResult(hit=False)
    allowed_intents = config.get("allowed_intents", [])
    system_prompt = config.get("system_prompt") or (
        f"判断以下用户输入的意图是否属于以下范围之一：{allowed_intents}。"
        "如果不属于，回答 yes；否则回答 no。只回答 yes 或 no。"
    )
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        result = await llm_model.ainvoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=text)]
        )
        answer = (result.content if hasattr(result, "content") else str(result)).strip().lower()
        if answer.startswith("yes"):
            return StrategyResult(hit=True, hit_detail={"intent_out_of_scope": True})
    except Exception as exc:
        logger.warning("Intent compliance LLM check failed: %s", exc)
    return StrategyResult(hit=False)


async def _check_rbac(text: str, config: dict[str, Any], **kw: Any) -> StrategyResult:
    """P-07 RBAC 权限前置校验。"""
    user_roles = set(kw.get("user_roles") or [])
    required_roles = set(config.get("required_roles", []))
    if required_roles and not required_roles.intersection(user_roles):
        return StrategyResult(
            hit=True,
            hit_detail={"required_roles": list(required_roles), "user_roles": list(user_roles)},
        )
    user_perms = set(kw.get("user_permissions") or [])
    required_perms = set(config.get("required_permissions", []))
    if required_perms and not required_perms.issubset(user_perms):
        missing = list(required_perms - user_perms)
        return StrategyResult(hit=True, hit_detail={"missing_permissions": missing})
    return StrategyResult(hit=False)


async def _check_business_rule(text: str, config: dict[str, Any], **kw: Any) -> StrategyResult:
    """P-08 业务前置硬性规则：时间窗口 / IP / 用户黑名单。"""
    for rule in config.get("rules", []):
        rule_type = rule.get("type")
        params = rule.get("params", {})
        if rule_type == "time":
            import datetime as _dt
            now_hour = _dt.datetime.now().hour
            allowed_hours = params.get("allowed_hours", list(range(24)))
            if now_hour not in allowed_hours:
                return StrategyResult(hit=True, hit_detail={"blocked_hour": now_hour})
        elif rule_type == "ip_blacklist":
            client_ip = kw.get("client_ip", "")
            if client_ip in params.get("ips", []):
                return StrategyResult(hit=True, hit_detail={"blocked_ip": client_ip})
        elif rule_type == "user_blacklist":
            user_id = kw.get("user_id", "")
            if user_id in params.get("users", []):
                return StrategyResult(hit=True, hit_detail={"blocked_user": user_id})
    return StrategyResult(hit=False)


async def _validate_result(text: str, config: dict[str, Any], **kw: Any) -> StrategyResult:
    """A-02 业务结果后置规则校验。"""
    for field_rule in config.get("field_rules", []):
        field_name = field_rule.get("field", "")
        pattern = field_rule.get("pattern", "")
        if pattern and not re.search(pattern, text):
            return StrategyResult(
                hit=True, hit_detail={"failed_field": field_name, "pattern": pattern}
            )
    return StrategyResult(hit=False)


STRATEGY_REGISTRY: dict[str, StrategyFunc] = {
    "rate_limit": _check_rate_limit,
    "identity_verify": _check_identity,
    "content_filter": _check_content_filter,
    "prompt_injection": _check_prompt_injection,
    "pii_desensitize": _desensitize_pii,
    "intent_compliance": _check_intent_compliance,
    "rbac_check": _check_rbac,
    "business_rule": _check_business_rule,
    "privacy_leak": _desensitize_pii,      # A-01 复用 PII 脱敏
    "result_validation": _validate_result,  # A-02
    # human_approval 由 detection_approval.py 单独处理
}


# ── Legacy keyword / LLM helpers (backward compatibility) ─────────────────────

def evaluate_keyword_rule(text: str, rule_content: dict[str, Any]) -> bool:
    """返回 True 表示检测命中（应拦截）。"""
    for kw in rule_content.get("keywords", []):
        if kw in text:
            return True
    for pattern in rule_content.get("patterns", []):
        if re.search(pattern, text):
            return True
    return False


async def _evaluate_llm_judge(rule: DetectionRule, text: str, llm_model: Any | None = None) -> bool:
    if llm_model is None:
        return False
    prompt_template: str = rule.rule_content.get("prompt", "判断以下内容是否有害，回答 yes 或 no：{text}")
    prompt = prompt_template.replace("{text}", text)
    try:
        result = await llm_model.ainvoke(prompt)
        answer = (result.content if hasattr(result, "content") else str(result)).strip().lower()
        return answer.startswith("yes")
    except Exception:
        return False


async def evaluate_rule(rule: DetectionRule, text: str, llm_model: Any | None = None) -> bool:
    """单条规则评估（向后兼容）。"""
    strategy_type = getattr(rule, "strategy_type", None)
    if strategy_type and strategy_type in STRATEGY_REGISTRY:
        result = await STRATEGY_REGISTRY[strategy_type](
            text, rule.rule_content or {}, llm_model=llm_model
        )
        return result.hit
    if rule.rule_type == RuleType.KEYWORD:
        return evaluate_keyword_rule(text, rule.rule_content)
    if rule.rule_type == RuleType.LLM_JUDGE:
        return await _evaluate_llm_judge(rule, text, llm_model)
    return False


# ── Internal event writer ──────────────────────────────────────────────────────

async def _write_detection_event(
    db: Any,
    *,
    agent_id: int,
    rule: DetectionRule,
    session_id: str | None,
    stage: str,
    action_taken: str,
    hit_detail: dict[str, Any],
    input_snapshot: str,
    status: str,
) -> None:
    try:
        from src.models.detection_event import DetectionEvent
        event = DetectionEvent(
            agent_id=agent_id,
            rule_id=rule.id,
            session_id=session_id,
            stage=stage,
            strategy_type=getattr(rule, "strategy_type", "content_filter"),
            action_taken=action_taken,
            hit_detail=hit_detail,
            input_snapshot=input_snapshot[:500] if input_snapshot else None,
            status=status,
        )
        db.add(event)
        await db.flush()
    except Exception as exc:
        logger.warning("Failed to write DetectionEvent: %s", exc)


# ── Core detection runners ─────────────────────────────────────────────────────

async def run_pre_detection(
    rules: list[DetectionRule],
    query: str,
    *,
    agent_id: int | None = None,
    session_id: str | None = None,
    db: Any | None = None,
    llm_model: Any | None = None,
    **extra_ctx: Any,
) -> str:
    """
    执行前置检测。返回（可能已改写的）查询文本。
    block/retry/escalate → 抛 PreCheckRejected；rewrite → 替换文本；其他 → 记录继续。
    原有调用方 (query_service.py) 不传 db/agent_id，返回值可忽略，行为不变。
    """
    logger.info("Running pre-detection for query: %.80s", query)
    text = query

    for rule in rules:
        if not rule.enabled:
            continue

        strategy_type = getattr(rule, "strategy_type", None)
        action_type = getattr(rule, "action_type", "block")
        merged_config = rule.rule_content or {}

        if strategy_type and strategy_type in STRATEGY_REGISTRY:
            result = await STRATEGY_REGISTRY[strategy_type](
                text, merged_config, llm_model=llm_model, **extra_ctx
            )
        else:
            hit = evaluate_keyword_rule(text, merged_config)
            result = StrategyResult(hit=hit, hit_detail={})

        if not result.hit:
            continue

        event_status = "LOGGED"
        if action_type == "log_review":
            event_status = "PENDING_REVIEW"
        elif action_type == "escalate":
            event_status = "ESCALATED"

        if db is not None and agent_id is not None:
            await _write_detection_event(
                db,
                agent_id=agent_id,
                rule=rule,
                session_id=session_id,
                stage="PRE",
                action_taken=action_type,
                hit_detail=result.hit_detail,
                input_snapshot=text,
                status=event_status,
            )

        if action_type == "block":
            raise PreCheckRejected(rule.reject_message or "查询被前置检测拦截")
        elif action_type == "rewrite" and result.rewritten_text is not None:
            text = result.rewritten_text
        elif action_type == "retry":
            raise PreCheckRejected(rule.reject_message or "请求频率超限，请稍后重试")
        elif action_type == "escalate":
            raise PreCheckRejected(rule.reject_message or "请求需要人工审批")
        else:
            logger.info("Pre-detection rule %s hit (action=%s), continuing", rule.id, action_type)

    logger.info("Pre-detection passed for query: %.80s", text)
    return text


async def run_post_detection(
    rules: list[DetectionRule],
    answer: str,
    *,
    agent_id: int | None = None,
    session_id: str | None = None,
    db: Any | None = None,
    llm_model: Any | None = None,
    **extra_ctx: Any,
) -> str:
    """
    执行后置检测。返回（可能已改写的）响应文本。
    A-03 人机审批由调用方（query_service.py）负责调用 detection_approval.py。
    """
    text = answer

    for rule in rules:
        if not rule.enabled:
            continue

        strategy_type = getattr(rule, "strategy_type", None)
        action_type = getattr(rule, "action_type", "block")
        merged_config = rule.rule_content or {}

        if strategy_type and strategy_type in STRATEGY_REGISTRY:
            result = await STRATEGY_REGISTRY[strategy_type](
                text, merged_config, llm_model=llm_model, **extra_ctx
            )
        else:
            hit = evaluate_keyword_rule(text, merged_config)
            result = StrategyResult(hit=hit, hit_detail={})

        if not result.hit:
            continue

        event_status = "LOGGED"
        if action_type == "log_review":
            event_status = "PENDING_REVIEW"
        elif action_type == "escalate":
            event_status = "ESCALATED"

        if db is not None and agent_id is not None:
            await _write_detection_event(
                db,
                agent_id=agent_id,
                rule=rule,
                session_id=session_id,
                stage="POST",
                action_taken=action_type,
                hit_detail=result.hit_detail,
                input_snapshot=text,
                status=event_status,
            )

        if action_type == "block":
            raise PostCheckRejected(rule.reject_message or "输出被后置检测拦截")
        elif action_type == "rewrite" and result.rewritten_text is not None:
            text = result.rewritten_text
        elif action_type == "escalate":
            raise PostCheckRejected(rule.reject_message or "响应需要人工审批")
        else:
            logger.info("Post-detection rule %s hit (action=%s), continuing", rule.id, action_type)

    return text
