"""测试公共样例。"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from polymarket_quant.data.schemas import (
    Market,
    MarketType,
    OrderBookLevel,
    OrderBookSnapshot,
    PriceTick,
)


@pytest.fixture
def base_ts() -> datetime:
    """固定测试时间。"""

    return datetime(2026, 6, 7, 8, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def market(base_ts: datetime) -> Market:
    """二元加密预测市场样例。"""

    return Market(
        condition_id="cond-btc-65000",
        question="Will BTC be above 65000 at expiry?",
        token_id_yes="yes-token",
        token_id_no="no-token",
        category="crypto",
        end_date=base_ts,
        active=True,
    )


def make_book(
    token_id: str,
    bid: str,
    ask: str,
    ts: datetime,
    bid_size: str = "10",
    ask_size: str = "10",
) -> OrderBookSnapshot:
    """构造订单簿样例。"""

    return OrderBookSnapshot(
        token_id=token_id,
        bids=[OrderBookLevel(price=Decimal(bid), size=Decimal(bid_size))],
        asks=[OrderBookLevel(price=Decimal(ask), size=Decimal(ask_size))],
        event_ts=ts,
        recv_ts=ts,
    )


def make_tick(ts: datetime, price: str = "70000") -> PriceTick:
    """构造 Binance tick 样例。"""

    return PriceTick(
        symbol="BTCUSDT",
        market_type=MarketType.PERP,
        price=Decimal(price),
        event_ts=ts,
        recv_ts=ts,
    )

