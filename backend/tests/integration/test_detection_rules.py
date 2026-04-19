"""
检测规则集成测试（T026）
测试 keyword 规则匹配（含正则）和 llm_judge 规则逻辑
"""
import re
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app


@pytest.mark.asyncio
async def test_create_keyword_rule():
    """创建 keyword 类型检测规则"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/detection-rules", json={
            "name": "敏感词检测",
            "stage": "PRE",
            "rule_type": "keyword",
            "rule_content": {"keywords": ["炸弹", "毒品"]},
            "reject_message": "含敏感词",
            "priority": 10,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["name"] == "敏感词检测"
        assert data["stage"] == "PRE"
        assert data["rule_type"] == "keyword"
        assert data["enabled"] is True


@pytest.mark.asyncio
async def test_keyword_rule_exact_match():
    """keyword 规则：精确词匹配"""
    from src.agents.detection import evaluate_keyword_rule

    rule_content = {"keywords": ["炸弹", "毒品"]}
    assert evaluate_keyword_rule("如何制造炸弹", rule_content) is True
    assert evaluate_keyword_rule("今天天气不错", rule_content) is False
    assert evaluate_keyword_rule("购买毒品渠道", rule_content) is True


@pytest.mark.asyncio
async def test_keyword_rule_regex_match():
    """keyword 规则：支持正则表达式匹配"""
    from src.agents.detection import evaluate_keyword_rule

    rule_content = {"patterns": [r"\b\d{4}-\d{4}-\d{4}-\d{4}\b"]}
    assert evaluate_keyword_rule("我的卡号是 1234-5678-9012-3456", rule_content) is True
    assert evaluate_keyword_rule("普通文本内容", rule_content) is False


@pytest.mark.asyncio
async def test_detection_rule_list_with_stage_filter():
    """按 stage 筛选检测规则列表"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for i, stage in enumerate(["PRE", "PRE", "POST"]):
            await client.post("/api/v1/detection-rules", json={
                "name": f"规则{i}",
                "stage": stage,
                "rule_type": "keyword",
                "rule_content": {"keywords": [f"词{i}"]},
            })

        resp = await client.get("/api/v1/detection-rules?stage=PRE")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        items = body["data"]["items"]
        assert all(r["stage"] == "PRE" for r in items)
        assert len(items) == 2


@pytest.mark.asyncio
async def test_detection_rule_toggle():
    """切换检测规则启用状态"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/detection-rules", json={
            "name": "可切换规则",
            "stage": "POST",
            "rule_type": "keyword",
            "rule_content": {"keywords": ["test"]},
        })
        rule_id = resp.json()["data"]["id"]

        resp = await client.patch(f"/api/v1/detection-rules/{rule_id}/toggle", json={"enabled": False})
        assert resp.status_code == 200
        assert resp.json()["data"]["enabled"] is False

        resp = await client.patch(f"/api/v1/detection-rules/{rule_id}/toggle", json={"enabled": True})
        assert resp.json()["data"]["enabled"] is True


@pytest.mark.asyncio
async def test_llm_judge_rule_creation():
    """创建 llm_judge 类型检测规则"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/detection-rules", json={
            "name": "LLM 安全检测",
            "stage": "PRE",
            "rule_type": "llm_judge",
            "rule_content": {
                "prompt": "判断以下内容是否包含有害信息，回答 yes 或 no：{text}",
                "llm_model_id": None,
            },
            "reject_message": "LLM 判定内容不安全",
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
        assert resp.json()["data"]["rule_type"] == "llm_judge"


@pytest.mark.asyncio
async def test_detection_rule_priority_ordering():
    """检测规则按优先级排序（priority 小的先执行）"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for priority, name in [(100, "低优先级"), (10, "高优先级"), (50, "中优先级")]:
            await client.post("/api/v1/detection-rules", json={
                "name": name,
                "stage": "PRE",
                "rule_type": "keyword",
                "rule_content": {"keywords": [name]},
                "priority": priority,
            })

        resp = await client.get("/api/v1/detection-rules?stage=PRE&page_size=10")
        items = resp.json()["data"]["items"]
        priorities = [r["priority"] for r in items]
        assert priorities == sorted(priorities), "规则未按 priority 升序返回"
