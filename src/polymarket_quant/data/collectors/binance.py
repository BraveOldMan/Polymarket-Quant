"""Binance 实时 collector 骨架。"""

from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic import BaseModel

from polymarket_quant.data.collectors.base import CollectorHealth
from polymarket_quant.data.collectors.polymarket import LiveCollectorDisabledError


class BinanceLiveCollector:
    """Binance 只读行情采集器骨架。

    首轮不强制接公网，避免实时 API 抖动影响离线验收。
    """

    name = "binance-live"

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self._running = False
        self._errors = 0
        self._last_error: str | None = None

    async def start(self) -> None:
        """启动实时采集器；默认 fail-closed。"""

        if not self.enabled:
            self._last_error = "live_collector_disabled"
            self._errors += 1
            raise LiveCollectorDisabledError("Binance 实时采集器默认关闭")
        raise NotImplementedError("实时 Binance 采集将在 P1 离线闭环后实现")

    async def stop(self) -> None:
        """停止实时采集器。"""

        self._running = False

    async def stream(self) -> AsyncIterator[BaseModel]:
        """实时事件流占位。"""

        if not self._running:
            return
        return
        yield

    async def health(self) -> CollectorHealth:
        """返回健康状态。"""

        return CollectorHealth(
            name=self.name,
            running=self._running,
            errors=self._errors,
            last_error=self._last_error,
        )

