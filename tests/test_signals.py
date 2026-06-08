"""P1 信号测试。"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from polymarket_quant.data.schemas import FairValueEstimate, Side, SignalStrategy
from polymarket_quant.data.signals.latency_arb import (
    LatencyConfig,
    find_latency_signals,
)
from polymarket_quant.data.signals.structural import (
    StructuralConfig,
    find_structural_signals,
)
from tests.conftest import make_book


def test_structural_signal_for_complete_set_discount(market, base_ts) -> None:
    """YES+NO 扣成本后低于 1 时产出结构信号。"""

    yes_book = make_book("yes-token", "0.45", "0.47", base_ts)
    no_book = make_book("no-token", "0.48", "0.49", base_ts)

    signals = find_structural_signals(
        market,
        yes_book,
        no_book,
        StructuralConfig(cost_bps=Decimal("50"), min_edge=Decimal("0.005")),
    )

    assert len(signals) == 1
    signal = signals[0]
    assert signal.strategy is SignalStrategy.SINGLE
    assert signal.edge_after_cost == Decimal("0.035")
    assert [leg.side for leg in signal.legs] == [Side.YES, Side.NO]


def test_structural_signal_rejects_no_edge(market, base_ts) -> None:
    """无净边际时不输出结构信号。"""

    yes_book = make_book("yes-token", "0.50", "0.51", base_ts)
    no_book = make_book("no-token", "0.48", "0.49", base_ts)

    signals = find_structural_signals(
        market,
        yes_book,
        no_book,
        StructuralConfig(cost_bps=Decimal("100"), min_edge=Decimal("0.005")),
    )

    assert signals == []


def test_latency_signal_requires_time_alignment(market, base_ts) -> None:
    """超过 Δ_max 的跨源数据不产出延时信号。"""

    yes_book = make_book("yes-token", "0.54", "0.56", base_ts)
    fair_value = FairValueEstimate(
        condition_id=market.condition_id,
        fair_prob=Decimal("0.70"),
        conf_lo=Decimal("0.65"),
        conf_hi=Decimal("0.75"),
        basis="latency_arb",
        inputs_ref=["tick:late"],
        ts=base_ts - timedelta(milliseconds=500),
    )

    signals = find_latency_signals(
        market,
        yes_book,
        fair_value,
        LatencyConfig(delta_max_ms=250),
    )

    assert signals == []


def test_latency_signal_for_yes_discount(market, base_ts) -> None:
    """公允概率显著高于市价且扣成本后达标时买 YES。"""

    yes_book = make_book("yes-token", "0.54", "0.56", base_ts)
    fair_value = FairValueEstimate(
        condition_id=market.condition_id,
        fair_prob=Decimal("0.70"),
        conf_lo=Decimal("0.65"),
        conf_hi=Decimal("0.75"),
        basis="latency_arb",
        inputs_ref=["tick:aligned"],
        ts=base_ts,
    )

    signals = find_latency_signals(
        market,
        yes_book,
        fair_value,
        LatencyConfig(cost_bps=Decimal("50"), min_edge=Decimal("0.005")),
    )

    assert len(signals) == 1
    assert signals[0].strategy is SignalStrategy.LATENCY
    assert signals[0].side is Side.YES
    assert signals[0].edge_after_cost == Decimal("0.145")


def test_latency_signal_rejects_interval_crossing_market(market, base_ts) -> None:
    """置信区间跨过市价时不产信号。"""

    yes_book = make_book("yes-token", "0.54", "0.56", base_ts)
    fair_value = FairValueEstimate(
        condition_id=market.condition_id,
        fair_prob=Decimal("0.58"),
        conf_lo=Decimal("0.52"),
        conf_hi=Decimal("0.64"),
        basis="latency_arb",
        inputs_ref=["tick:uncertain"],
        ts=base_ts,
    )

    assert find_latency_signals(market, yes_book, fair_value) == []

