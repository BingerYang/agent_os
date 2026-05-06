"""
检测中间件（T033）
基于 LangChain 1.0 Middleware 概念实现前/后置检测。
检测失败时抛出 PreCheckRejected / PostCheckRejected。
"""
import re
import logging
from typing import Any

from src.core.exceptions import PreCheckRejected, PostCheckRejected
from src.models.detection_rule import DetectionRule, RuleType

logger = logging.getLogger()


def evaluate_keyword_rule(text: str, rule_content: dict[str, Any]) -> bool:
    """
    返回 True 表示检测命中（应拦截）。
    支持 keywords（精确包含）和 patterns（正则）。
    """
    for kw in rule_content.get("keywords", []):
        if kw in text:
            return True
    for pattern in rule_content.get("patterns", []):
        if re.search(pattern, text):
            return True
    return False


async def evaluate_rule(rule: DetectionRule, text: str, llm_model: Any | None = None) -> bool:
    """对单条规则做评估，返回 True 表示命中（拦截）。"""
    if rule.rule_type == RuleType.KEYWORD:
        return evaluate_keyword_rule(text, rule.rule_content)
    if rule.rule_type == RuleType.LLM_JUDGE:
        return await _evaluate_llm_judge(rule, text, llm_model)
    return False


async def _evaluate_llm_judge(rule: DetectionRule, text: str, llm_model: Any | None = None) -> bool:
    """LLM 裁判规则：调用 LLM 判断是否拦截。"""
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


async def run_pre_detection(
        rules: list[DetectionRule],
        query: str,
        llm_model: Any | None = None,
) -> None:
    """
    对查询文本执行所有前置检测规则（按 priority 升序）。
    任一规则命中则抛出 PreCheckRejected。
    """
    logger.info("Running pre-detection for query: %s", query)
    for rule in rules:
        if not rule.enabled:
            continue
        if await evaluate_rule(rule, query, llm_model):
            msg = rule.reject_message or "查询被前置检测拦截"
            raise PreCheckRejected(msg)
    logger.info("Pre-detection passed for query: %s", query)


async def run_post_detection(
        rules: list[DetectionRule],
        answer: str,
        llm_model: Any | None = None,
) -> None:
    """
    对 Agent 输出执行所有后置检测规则（按 priority 升序）。
    任一规则命中则抛出 PostCheckRejected。
    """
    for rule in rules:
        if not rule.enabled:
            continue
        if await evaluate_rule(rule, answer, llm_model):
            msg = rule.reject_message or "输出被后置检测拦截"
            raise PostCheckRejected(msg)
