"""离线 replay collector。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

from pydantic import BaseModel

from polymarket_quant.data.collectors.base import CollectorHealth


class ReplayCollector:
    """从内存事件序列回放已校验模型。

    该 collector 用于测试和离线回放，不访问网络，也不产生任何交易动作。
    """

    def __init__(self, name: str, events: Sequence[BaseModel]) -> None:
        self.name = name
        self._events = list(events)
        self._running = False
        self._errors = 0
        self._last_error: str | None = None

    async def start(self) -> None:
        """标记 replay 开始。"""

        self._running = True

    async def stop(self) -> None:
        """标记 replay 停止。"""

        self._running = False

    async def stream(self) -> AsyncIterator[BaseModel]:
        """按传入顺序产出事件。"""

        if not self._running:
            self._last_error = "collector_not_started"
            self._errors += 1
            return
        for event in self._events:
            yield event

    async def health(self) -> CollectorHealth:
        """返回 replay collector 健康状态。"""

        return CollectorHealth(
            name=self.name,
            running=self._running,
            errors=self._errors,
            last_error=self._last_error,
        )

