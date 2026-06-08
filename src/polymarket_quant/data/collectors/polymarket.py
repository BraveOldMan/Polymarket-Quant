"""Polymarket 实时 collector 骨架。"""

from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic import BaseModel

from polymarket_quant.data.collectors.base import CollectorHealth


class LiveCollectorDisabledError(RuntimeError):
    """实时 collector 默认关闭。"""


class PolymarketLiveCollector:
    """Polymarket 只读实时采集器骨架。

    首轮离线闭环不启用实时网络连接；该类保留接口位置，避免信号层依赖
    第三方原始格式。后续实现也只能读取市场数据，不能接触交易执行。
    """

    name = "polymarket-live"

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
            raise LiveCollectorDisabledError("Polymarket 实时采集器默认关闭")
        raise NotImplementedError("实时 Polymarket 采集将在 P1 离线闭环后实现")

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

