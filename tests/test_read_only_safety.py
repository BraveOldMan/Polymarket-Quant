"""只读安全边界测试。"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from polymarket_quant.data.schemas import ArbSignal, Side, SignalStrategy
from polymarket_quant.orchestration import DecisionStatus, ReadOnlyOrchestrator
from polymarket_quant.settlement import (
    ReadOnlySettlementClient,
    SettlementIntent,
    SettlementMechanism,
    SettlementStatus,
)


def test_source_has_no_execution_call_patterns() -> None:
    """源码中不得出现真实交易、签名或链上写入调用形态。"""

    forbidden = [
        r"\bcreate_order\s*\(",
        r"\bsign_message\s*\(",
        r"\bsign_transaction\s*\(",
        r"\bapprove\s*\(",
        r"\bsplit\s*\(",
        r"\bmerge\s*\(",
        r"\bredeem\s*\(",
        r"\bconvert\s*\(",
    ]
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src").rglob("*.py")
    )

    for pattern in forbidden:
        assert re.search(pattern, source) is None


def test_orchestrator_rejects_execution_by_default(base_ts) -> None:
    """编排层默认只读并被风控 kill-switch 否决。"""

    signal = ArbSignal(
        strategy=SignalStrategy.LATENCY,
        condition_id="cond",
        side=Side.YES,
        market_prob=Decimal("0.50"),
        fair_prob=Decimal("0.60"),
        edge=Decimal("0.10"),
        edge_after_cost=Decimal("0.09"),
        confidence=Decimal("0.90"),
        ts=base_ts,
    )

    decision = ReadOnlyOrchestrator().evaluate(signal)

    assert decision.status is DecisionStatus.VETOED
    assert decision.reason == "kill_switch_active"


def test_settlement_client_is_disabled() -> None:
    """结算层默认 disabled，不访问钱包或链上。"""

    intent = SettlementIntent(
        intent_id="intent-1",
        condition_id="cond",
        mechanism=SettlementMechanism.CTF,
        nonce_key="nonce-1",
    )

    result = ReadOnlySettlementClient().submit_intent(intent)

    assert result.status is SettlementStatus.DISABLED
    assert result.reason == "read_only_stage"

