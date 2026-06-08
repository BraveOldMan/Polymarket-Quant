"""洗盘与流动性过滤测试。"""

from __future__ import annotations

from decimal import Decimal

from polymarket_quant.data.signals.liquidity import (
    LiquidityConfig,
    is_exit_liquidity_ok,
)
from polymarket_quant.data.signals.structural import find_structural_signals
from polymarket_quant.data.signals.wash_filter import assess_order_book_wash
from tests.conftest import make_book


def test_wash_filter_marks_extreme_crossed_book(base_ts) -> None:
    """极端高买价和极端低卖价同时放量时标记疑似洗盘。"""

    book = make_book(
        "yes-token",
        "0.98",
        "0.03",
        base_ts,
        bid_size="200",
        ask_size="200",
    )

    assessment = assess_order_book_wash(book)

    assert assessment.is_suspect is True
    assert "extreme_crossed_book" in assessment.reasons


def test_liquidity_filter_rejects_insufficient_depth(base_ts) -> None:
    """可接受滑点内 bid 深度不足时拒绝。"""

    book = make_book("yes-token", "0.50", "0.55", base_ts, bid_size="0.5")

    assert is_exit_liquidity_ok(
        book,
        LiquidityConfig(target_size=Decimal("1")),
    ) is False


def test_structural_signal_filtered_by_wash(market, base_ts) -> None:
    """洗盘命中时默认不产可交易信号。"""

    yes_book = make_book("yes-token", "0.45", "0.47", base_ts)
    no_book = make_book("no-token", "0.48", "0.49", base_ts)

    assert find_structural_signals(
        market,
        yes_book,
        no_book,
        wash_suspect=True,
    ) == []


def test_structural_signal_filtered_by_liquidity(market, base_ts) -> None:
    """出场流动性不足时默认不产可交易信号。"""

    yes_book = make_book("yes-token", "0.45", "0.47", base_ts)
    no_book = make_book("no-token", "0.48", "0.49", base_ts)

    assert find_structural_signals(
        market,
        yes_book,
        no_book,
        exit_liquidity_ok=False,
    ) == []

