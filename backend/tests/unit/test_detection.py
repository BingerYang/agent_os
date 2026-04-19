from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.detection import run_post_detection
from src.core.exceptions import PostCheckRejected
from src.models.detection_rule import DetectionRule, DetectionStage, RuleType


def _build_rule(*, rule_type: RuleType, rule_content: dict) -> DetectionRule:
    return DetectionRule(
        name="test-rule",
        stage=DetectionStage.POST,
        rule_type=rule_type,
        rule_content=rule_content,
        reject_message="blocked",
        priority=1,
        enabled=True,
    )


@pytest.mark.asyncio
async def test_keyword_rule_match_literal():
    rule = _build_rule(
        rule_type=RuleType.KEYWORD,
        rule_content={"keywords": ["禁止词"]},
    )

    with pytest.raises(PostCheckRejected, match="blocked"):
        await run_post_detection([rule], "这段文本包含禁止词")


@pytest.mark.asyncio
async def test_keyword_rule_match_regex():
    rule = _build_rule(
        rule_type=RuleType.KEYWORD,
        rule_content={"patterns": [r"\d{3}-\d{4}"]},
    )

    with pytest.raises(PostCheckRejected, match="blocked"):
        await run_post_detection([rule], "联系电话是 123-4567")


@pytest.mark.asyncio
async def test_keyword_rule_no_match():
    rule = _build_rule(
        rule_type=RuleType.KEYWORD,
        rule_content={"patterns": [r"\d{3}-\d{4}"]},
    )

    await run_post_detection([rule], "文本里没有电话号码")


@pytest.mark.asyncio
async def test_llm_judge_rule_mock_reject():
    rule = _build_rule(
        rule_type=RuleType.LLM_JUDGE,
        rule_content={"prompt": "判断是否拦截：{text}"},
    )

    llm_model = AsyncMock()
    llm_model.ainvoke.return_value = SimpleNamespace(content="yes")

    with patch.object(llm_model, "ainvoke", new=llm_model.ainvoke):
        with pytest.raises(PostCheckRejected, match="blocked"):
            await run_post_detection([rule], "需要被拦截的回复", llm_model=llm_model)


@pytest.mark.asyncio
async def test_llm_judge_rule_mock_pass():
    rule = _build_rule(
        rule_type=RuleType.LLM_JUDGE,
        rule_content={"prompt": "判断是否拦截：{text}"},
    )

    llm_model = AsyncMock()
    llm_model.ainvoke.return_value = SimpleNamespace(content="no")

    with patch.object(llm_model, "ainvoke", new=llm_model.ainvoke):
        await run_post_detection([rule], "正常回复", llm_model=llm_model)
