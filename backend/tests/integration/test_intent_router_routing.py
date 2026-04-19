"""
意图路由单元测试（T043）
测试路由置信度计算、单/多 Agent 路由分支逻辑
"""
import pytest
from src.agents.intent_router import route_intent, route_multi_agent, IntentResult, RouteResult


@pytest.mark.asyncio
async def test_route_intent_no_tools_returns_empty():
    """无可用工具时返回空选择列表"""
    result = await route_intent("测试查询", tools=[], llm_model=None)
    assert isinstance(result, IntentResult)
    assert result.selected_tools == []
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_route_intent_no_llm_selects_all_tools():
    """无 LLM 时默认选择全部工具"""
    class FakeTool:
        name = "tool_a"

    result = await route_intent("测试查询", tools=[FakeTool()], llm_model=None)
    assert "tool_a" in result.selected_tools


@pytest.mark.asyncio
async def test_route_multi_agent_no_llm_selects_all():
    """无 LLM 时多 Agent 路由默认选择所有子 Agent"""
    class FakeAgent:
        id = 1
        name = "子Agent1"

    result = await route_multi_agent(
        query="复杂查询",
        sub_agents=[FakeAgent()],
        llm_model=None,
        confidence_threshold=0.7,
    )
    assert isinstance(result, RouteResult)
    assert len(result.target_agent_ids) > 0
    assert result.confidence >= 0.0


@pytest.mark.asyncio
async def test_route_multi_agent_returns_route_result():
    """route_multi_agent 返回 RouteResult 对象"""
    class FakeAgent:
        id = 2
        name = "子Agent2"

    result = await route_multi_agent(
        query="简单查询",
        sub_agents=[FakeAgent()],
        llm_model=None,
        confidence_threshold=0.5,
    )
    assert hasattr(result, "target_agent_ids")
    assert hasattr(result, "confidence")
    assert hasattr(result, "route_reason")
    assert isinstance(result.target_agent_ids, list)
