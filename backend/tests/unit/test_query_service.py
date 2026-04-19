from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.intent_router import IntentResult
from src.core.exceptions import PreCheckRejected
from src.models.pipeline import PipelineType
from src.services.query_service import execute_query


def _build_single_agent_pipeline():
    tool = SimpleNamespace(id=11, name="weather")
    agent = SimpleNamespace(id=1, tools=[tool], llm_model=object())
    pipeline = SimpleNamespace(
        pipeline_type=PipelineType.SINGLE_AGENT,
        primary_agent=agent,
        sub_agents=[],
        detection_rules=[],
    )
    return pipeline, agent, tool


def _build_multi_agent_pipeline():
    orchestrator = SimpleNamespace(id=1)
    sub_agent = SimpleNamespace(id=2)
    pipeline = SimpleNamespace(
        pipeline_type=PipelineType.MULTI_AGENT,
        primary_agent=orchestrator,
        sub_agents=[sub_agent],
        detection_rules=[],
    )
    return pipeline, orchestrator, sub_agent


@pytest.mark.asyncio
async def test_single_agent_pipeline_routing():
    pipeline, agent, tool = _build_single_agent_pipeline()
    run_single_agent_mock = AsyncMock(
        return_value={
            "answer": "ok",
            "tools_called": ["weather"],
            "session_id": "sess-1",
            "latency_ms": 12,
        }
    )

    with patch("src.services.query_service._load_pipeline", new=AsyncMock(return_value=pipeline)), \
         patch("src.services.query_service._get_enabled_config", new=AsyncMock(return_value=({11}, {1}, set()))), \
         patch("src.services.query_service.run_pre_detection", new=AsyncMock()), \
         patch("src.services.query_service.route_intent", new=AsyncMock(return_value=IntentResult(selected_tools=["weather"]))), \
         patch("src.services.query_service.run_single_agent", new=run_single_agent_mock), \
         patch("src.services.query_service.run_post_detection", new=AsyncMock()):
        result = await execute_query(object(), 100, "查天气", session_id="sess-1")

    run_single_agent_mock.assert_awaited_once_with(agent, "查天气", [tool], "sess-1")
    assert result["answer"] == "ok"
    assert result["pipeline_type"] == "SINGLE_AGENT"


@pytest.mark.asyncio
async def test_multi_agent_pipeline_routing():
    pipeline, orchestrator, sub_agent = _build_multi_agent_pipeline()
    run_multi_agent_mock = AsyncMock(
        return_value={
            "answer": "ok",
            "tools_called": [],
            "session_id": "sess-2",
            "latency_ms": 23,
        }
    )
    run_single_agent_mock = AsyncMock()

    with patch("src.services.query_service._load_pipeline", new=AsyncMock(return_value=pipeline)), \
         patch("src.services.query_service._get_enabled_config", new=AsyncMock(return_value=(set(), {1, 2}, set()))), \
         patch("src.services.query_service.run_pre_detection", new=AsyncMock()), \
         patch("src.services.query_service.run_single_agent", new=run_single_agent_mock), \
         patch("src.agents.multi_agent.run_multi_agent", new=run_multi_agent_mock), \
         patch("src.services.query_service.run_post_detection", new=AsyncMock()):
        result = await execute_query(object(), 200, "多 Agent 查询", session_id="sess-2")

    run_multi_agent_mock.assert_awaited_once_with(
        pipeline,
        "多 Agent 查询",
        "sess-2",
        sub_agents=[sub_agent],
        orchestrator=orchestrator,
    )
    run_single_agent_mock.assert_not_awaited()
    assert result["answer"] == "ok"
    assert result["pipeline_type"] == "MULTI_AGENT"


@pytest.mark.asyncio
async def test_pre_detection_blocks_query():
    pipeline, _, _ = _build_single_agent_pipeline()
    run_single_agent_mock = AsyncMock()
    run_post_detection_mock = AsyncMock()

    with patch("src.services.query_service._load_pipeline", new=AsyncMock(return_value=pipeline)), \
         patch("src.services.query_service._get_enabled_config", new=AsyncMock(return_value=({11}, {1}, set()))), \
         patch("src.services.query_service.run_pre_detection", new=AsyncMock(side_effect=PreCheckRejected("blocked"))), \
         patch("src.services.query_service.run_single_agent", new=run_single_agent_mock), \
         patch("src.services.query_service.run_post_detection", new=run_post_detection_mock):
        with pytest.raises(PreCheckRejected, match="blocked"):
            await execute_query(object(), 300, "敏感查询")

    run_single_agent_mock.assert_not_awaited()
    run_post_detection_mock.assert_not_awaited()
