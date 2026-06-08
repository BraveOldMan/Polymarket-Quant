"""采集器协议。"""

from __future__ import annotations

from typing import AsyncIterator, Protocol

from pydantic import BaseModel, Field


class CollectorHealth(BaseModel):
    """采集器健康状态。"""

    name: str
    running: bool
    errors: int = Field(ge=0)
    last_error: str | None = None


class Collector(Protocol):
    """所有 collector 的统一生命周期协议。"""

    name: str

    async def start(self) -> None:
        """启动采集器。"""

    async def stop(self) -> None:
        """停止采集器。"""

    async def stream(self) -> AsyncIterator[BaseModel]:
        """持续产出已校验的内部事件。"""
        yield

    async def health(self) -> CollectorHealth:
        """返回可观测健康状态。"""

