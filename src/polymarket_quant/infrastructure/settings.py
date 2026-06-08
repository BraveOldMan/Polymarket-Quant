"""运行配置。"""

from __future__ import annotations

import os
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


def _env_bool(name: str, default: bool) -> bool:
    """读取布尔环境变量。"""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class AppSettings(BaseModel):
    """应用运行配置。

    首轮默认离线只读；任何实时、执行或链上能力必须显式改配置后另行实现。
    """

    mode: str = "offline"
    read_only: bool = True
    delta_max_ms: int = Field(default=250, ge=0)
    cost_bps: Decimal = Field(default=Decimal("100"), ge=Decimal("0"))
    min_edge: Decimal = Field(default=Decimal("0.005"), ge=Decimal("0"))
    polymarket_gamma_base_url: str | None = None
    polymarket_clob_base_url: str | None = None
    binance_ws_base_url: str | None = None
    polygon_rpc_url: str | None = None

    @classmethod
    def from_env(cls) -> AppSettings:
        """从环境变量读取配置。"""

        return cls(
            mode=os.getenv("POLYMARKET_QUANT_MODE", "offline"),
            read_only=_env_bool("POLYMARKET_QUANT_READ_ONLY", True),
            delta_max_ms=int(os.getenv("POLYMARKET_QUANT_DELTA_MAX_MS", "250")),
            cost_bps=Decimal(os.getenv("POLYMARKET_QUANT_COST_BPS", "100")),
            min_edge=Decimal(os.getenv("POLYMARKET_QUANT_MIN_EDGE", "0.005")),
            polymarket_gamma_base_url=os.getenv("POLYMARKET_GAMMA_BASE_URL") or None,
            polymarket_clob_base_url=os.getenv("POLYMARKET_CLOB_BASE_URL") or None,
            binance_ws_base_url=os.getenv("BINANCE_WS_BASE_URL") or None,
            polygon_rpc_url=os.getenv("POLYGON_RPC_URL") or None,
        )

    @model_validator(mode="after")
    def validate_read_only_first(self) -> AppSettings:
        """P1 阶段必须保持只读。"""

        if self.mode == "offline" and not self.read_only:
            raise ValueError("offline 模式必须保持 read_only=true")
        return self

