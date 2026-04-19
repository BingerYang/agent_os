"""
Event Bus 集成测试（T059）

按 TDD 编写：当前运行时应保持失败，不实现业务代码。
"""
from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


def _get_event_bus_class():
    try:
        from src.services.event_bus import EventBus
    except ModuleNotFoundError:
        EventBus = None

    assert EventBus is not None, "Expected src.services.event_bus.EventBus to exist for T059"
    return EventBus


@pytest.mark.asyncio
async def test_publish_and_subscribe():
    """EventBus 应支持发布事件并让订阅者收到同一份 payload。"""
    EventBus = _get_event_bus_class()
    event_bus = EventBus()
    subscriber = event_bus.subscribe()
    payload = {"entity_type": "tool", "entity_id": 1, "action": "enable"}

    try:
        receive_task = asyncio.create_task(subscriber.__anext__())
        await asyncio.sleep(0)
        await event_bus.publish(payload)
        received = await asyncio.wait_for(receive_task, timeout=1)
    finally:
        await subscriber.aclose()

    assert received == payload


@pytest.mark.asyncio
async def test_sse_stream_format():
    """GET /api/v1/events/stream 应返回标准 SSE 流。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("GET", "/api/v1/events/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            lines = response.aiter_lines()
            first_line = await asyncio.wait_for(lines.__anext__(), timeout=2)
            assert first_line.startswith("data:")


@pytest.mark.asyncio
async def test_ping_keepalive():
    """无业务事件时，订阅流也应在 ping_interval 内返回 ping 帧。"""
    EventBus = _get_event_bus_class()
    event_bus = EventBus(ping_interval=1)
    subscriber = event_bus.subscribe()

    try:
        frame = await asyncio.wait_for(subscriber.__anext__(), timeout=2)
    finally:
        await subscriber.aclose()

    assert frame["event_type"] == "ping"
