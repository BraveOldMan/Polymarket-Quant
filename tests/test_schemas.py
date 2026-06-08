"""数据契约测试。"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from polymarket_quant.data.schemas import (
    ArbSignal,
    FairValueEstimate,
    OrderBookLevel,
    OrderBookSnapshot,
    Side,
    SignalStrategy,
)


def test_order_book_mid_uses_best_prices(base_ts) -> None:
    """中间价使用最高 bid 和最低 ask。"""

    book = OrderBookSnapshot(
        token_id="yes-token",
        bids=[
            OrderBookLevel(price=Decimal("0.40"), size=Decimal("1")),
            OrderBookLevel(price=Decimal("0.50"), size=Decimal("1")),
        ],
        asks=[
            OrderBookLevel(price=Decimal("0.70"), size=Decimal("1")),
            OrderBookLevel(price=Decimal("0.60"), size=Decimal("1")),
        ],
        event_ts=base_ts,
        recv_ts=base_ts,
    )

    assert book.mid == Decimal("0.55")


def test_invalid_probability_price_rejected() -> None:
    """概率价格必须位于 [0, 1]。"""

    with pytest.raises(ValidationError):
        OrderBookLevel(price=Decimal("1.01"), size=Decimal("1"))


def test_empty_order_book_fails_explicitly(base_ts) -> None:
    """空盘口不能静默产出中间价。"""

    book = OrderBookSnapshot(
        token_id="yes-token",
        bids=[],
        asks=[],
        event_ts=base_ts,
        recv_ts=base_ts,
    )

    with pytest.raises(ValueError):
        _ = book.mid


def test_fair_value_interval_must_cover_point(base_ts) -> None:
    """公允概率必须落在置信区间内。"""

    with pytest.raises(ValidationError):
        FairValueEstimate(
            condition_id="cond",
            fair_prob=Decimal("0.50"),
            conf_lo=Decimal("0.60"),
            conf_hi=Decimal("0.70"),
            basis="latency_arb",
            inputs_ref=[],
            ts=base_ts,
        )


def test_arb_signal_uses_independent_default_lists(base_ts) -> None:
    """ArbSignal 的列表默认值不能跨实例共享。"""

    first = ArbSignal(
        strategy=SignalStrategy.LATENCY,
        condition_id="cond-1",
        side=Side.YES,
        market_prob=Decimal("0.50"),
        fair_prob=Decimal("0.60"),
        edge=Decimal("0.10"),
        edge_after_cost=Decimal("0.09"),
        confidence=Decimal("0.90"),
        ts=base_ts,
    )
    second = ArbSignal(
        strategy=SignalStrategy.LATENCY,
        condition_id="cond-2",
        side=Side.YES,
        market_prob=Decimal("0.50"),
        fair_prob=Decimal("0.60"),
        edge=Decimal("0.10"),
        edge_after_cost=Decimal("0.09"),
        confidence=Decimal("0.90"),
        ts=base_ts + timedelta(seconds=1),
    )

    first.inputs_ref.append("x")

    assert second.inputs_ref == []


def test_extra_fields_are_rejected(base_ts) -> None:
    """上游 schema 漂移不能静默通过。"""

    with pytest.raises(ValidationError):
        OrderBookSnapshot.model_validate(
            {
                "token_id": "yes-token",
                "bids": [],
                "asks": [],
                "event_ts": base_ts,
                "recv_ts": base_ts,
                "unexpected": "field",
            }
        )
