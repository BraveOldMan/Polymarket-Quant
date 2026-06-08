"""只读编排器。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from polymarket_quant.data.schemas import ArbSignal
from polymarket_quant.risk.controls import RiskAgent, RiskStatus


class DecisionStatus(StrEnum):
    """编排决策状态。"""

    REJECTED = "rejected"
    VETOED = "vetoed"


class DecisionRecord(BaseModel):
    """编排决策记录。"""

    status: DecisionStatus
    reason: str
    signal_ref: str
    audit_summary: str
    evidence_refs: list[str] = Field(default_factory=list)


class ReadOnlyOrchestrator:
    """P1 只读编排器。

    该编排器保留多空辩论与风险否决入口，但不会生成执行动作。
    """

    def __init__(self, risk_agent: RiskAgent | None = None) -> None:
        self.risk_agent = risk_agent or RiskAgent()

    def evaluate(self, signal: ArbSignal) -> DecisionRecord:
        """评估信号并 fail-closed。"""

        risk_decision = self.risk_agent.evaluate(signal)
        signal_ref = f"{signal.strategy}:{signal.condition_id}:{signal.ts.isoformat()}"
        if risk_decision.status is RiskStatus.VETO:
            return DecisionRecord(
                status=DecisionStatus.VETOED,
                reason=risk_decision.reason,
                signal_ref=signal_ref,
                audit_summary="P1 只读阶段，风险代理否决任何执行请求。",
                evidence_refs=signal.inputs_ref,
            )
        return DecisionRecord(
            status=DecisionStatus.REJECTED,
            reason="read_only_mode",
            signal_ref=signal_ref,
            audit_summary="P1 只读阶段只记录信号，不生成执行动作。",
            evidence_refs=signal.inputs_ref,
        )

