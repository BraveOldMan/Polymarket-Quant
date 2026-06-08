"""风险控制接口。"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from polymarket_quant.data.schemas import ArbSignal


class RiskStatus(StrEnum):
    """风控状态。"""

    ALLOW = "allow"
    VETO = "veto"


class RiskLimits(BaseModel):
    """组合风控限额。"""

    max_signal_edge_cost_bps: Decimal = Field(default=Decimal("5000"), ge=0)
    kill_switch_active: bool = True


class RiskDecision(BaseModel):
    """风控判定结果。"""

    status: RiskStatus
    reason: str


class RiskAgent:
    """风险一票否决代理。

    P1 不进入执行链路，默认 kill-switch 打开，任何开仓请求都会被否决。
    """

    def __init__(self, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()

    def evaluate(self, signal: ArbSignal) -> RiskDecision:
        """对信号做风控判定。"""

        if self.limits.kill_switch_active:
            return RiskDecision(status=RiskStatus.VETO, reason="kill_switch_active")
        if signal.wash_suspect:
            return RiskDecision(status=RiskStatus.VETO, reason="wash_suspect")
        if not signal.exit_liquidity_ok:
            return RiskDecision(status=RiskStatus.VETO, reason="exit_liquidity_not_ok")
        return RiskDecision(status=RiskStatus.ALLOW, reason="risk_checks_passed")

