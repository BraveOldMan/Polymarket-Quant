"""离线 replay 测试。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from polymarket_quant.backtest.replay import ReplayConfig, run_single_market_replay
from polymarket_quant.data.schemas import (
    Market,
    OrderBookSnapshot,
    PriceTick,
    SignalStrategy,
)
from polymarket_quant.data.signals.latency_arb import LatencyConfig
from polymarket_quant.data.signals.structural import StructuralConfig


def test_offline_replay_outputs_p1_signals() -> None:
    """离线 fixture 能产出策略①和策略④信号。"""

    payload = json.loads(Path("tests/fixtures/offline_replay.json").read_text())
    market = Market.model_validate(payload["market"])
    yes_books = [
        OrderBookSnapshot.model_validate(item) for item in payload["yes_books"]
    ]
    no_books = [
        OrderBookSnapshot.model_validate(item) for item in payload["no_books"]
    ]
    ticks = [PriceTick.model_validate(item) for item in payload["ticks"]]

    result = run_single_market_replay(
        market=market,
        yes_books=yes_books,
        no_books=no_books,
        ticks=ticks,
        config=ReplayConfig(
            threshold_price=Decimal("65000"),
            expiry=datetime(2026, 6, 7, 9, 0, 0, tzinfo=timezone.utc),
            annualized_vol=Decimal("0.80"),
            structural=StructuralConfig(cost_bps=Decimal("100")),
            latency=LatencyConfig(cost_bps=Decimal("100")),
        ),
    )

    strategies = {signal.strategy for signal in result.signals}
    assert result.skipped_events == 0
    assert SignalStrategy.SINGLE in strategies
    assert SignalStrategy.LATENCY in strategies


def test_replay_does_not_use_future_tick(market, base_ts) -> None:
    """replay 不允许用未来 tick 补当前信号。"""

    yes_book = OrderBookSnapshot.model_validate(
        {
            "token_id": "yes-token",
            "bids": [{"price": "0.54", "size": "10"}],
            "asks": [{"price": "0.56", "size": "10"}],
            "event_ts": base_ts,
            "recv_ts": base_ts,
        }
    )
    no_book = OrderBookSnapshot.model_validate(
        {
            "token_id": "no-token",
            "bids": [{"price": "0.40", "size": "10"}],
            "asks": [{"price": "0.42", "size": "10"}],
            "event_ts": base_ts,
            "recv_ts": base_ts,
        }
    )
    future_tick = PriceTick.model_validate(
        {
            "symbol": "BTCUSDT",
            "market_type": "perp",
            "price": "70000",
            "event_ts": base_ts + timedelta(seconds=1),
            "recv_ts": base_ts + timedelta(seconds=1),
        }
    )

    result = run_single_market_replay(
        market=market,
        yes_books=[yes_book],
        no_books=[no_book],
        ticks=[future_tick],
        config=ReplayConfig(
            threshold_price=Decimal("65000"),
            expiry=base_ts + timedelta(hours=1),
            annualized_vol=Decimal("0.80"),
        ),
    )

    assert result.signals == []
    assert result.skipped_events == 1

