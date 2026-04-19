from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator

from src.services.config_cache import config_cache


class EventBus:
    def __init__(self, ping_interval: float = 30.0):
        self._queues: list[asyncio.Queue[dict]] = []
        self._ping_interval = ping_interval

    async def publish(self, event: dict) -> None:
        """广播事件到所有订阅队列"""
        config_cache.apply_event(event)
        for queue in list(self._queues):
            await queue.put(event)

    def subscribe(self) -> AsyncGenerator[dict, None]:
        """返回异步生成器，自动注册/注销队列，定时发送 ping"""

        async def _generator() -> AsyncGenerator[dict, None]:
            queue: asyncio.Queue[dict] = asyncio.Queue()
            self._queues.append(queue)
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=self._ping_interval)
                        yield event
                    except asyncio.TimeoutError:
                        yield {
                            "event_type": "ping",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
            except (asyncio.CancelledError, GeneratorExit):
                raise
            finally:
                await self._cleanup(queue)

        return _generator()

    async def _cleanup(self, queue: asyncio.Queue) -> None:
        """从订阅列表移除队列"""
        if queue in self._queues:
            self._queues.remove(queue)


event_bus = EventBus(ping_interval=30.0)
