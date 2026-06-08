"""离线 replay 验证。

该模块只验证数据时间口径和信号规则，不计算收益、夏普或实盘结论。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TypeVar

from polymarket_quant.data.schemas import (
    ArbSignal,
    Market,
    OrderBookSnapshot,
    PriceTick,
)
from polymarket_quant.data.signals.fair_value import estimate_threshold_probability
from polymarket_quant.data.signals.latency_arb import (
    LatencyConfig,
    find_latency_signals,
)
from polymarket_quant.data.signals.liquidity import (
    LiquidityConfig,
    is_exit_liquidity_ok,
)
from polymarket_quant.data.signals.structural import (
    StructuralConfig,
    find_structural_signals,
)
from polymarket_quant.data.signals.wash_filter import assess_order_book_wash

TEvent = TypeVar("TEvent", OrderBookSnapshot, PriceTick)


@dataclass(frozen=True)
class ReplayConfig:
    """单市场离线 replay 参数。"""

    threshold_price: Decimal
    expiry: datetime
    annualized_vol: Decimal
    structural: StructuralConfig = field(default_factory=StructuralConfig)
    latency: LatencyConfig = field(default_factory=LatencyConfig)
    liquidity: LiquidityConfig = field(default_factory=LiquidityConfig)


@dataclass(frozen=True)
class ReplayResult:
    """离线 replay 结果。"""

    signals: list[ArbSignal]
    skipped_events: int


def _latest_not_after(events: list[TEvent], recv_ts: datetime) -> TEvent | None:
    """返回不晚于目标接收时刻的最新事件，防止前视。"""

    candidates = [event for event in events if event.recv_ts <= recv_ts]
    if not candidates:
        return None
    return max(candidates, key=lambda event: event.recv_ts)


def run_single_market_replay(
    market: Market,
    yes_books: list[OrderBookSnapshot],
    no_books: list[OrderBookSnapshot],
    ticks: list[PriceTick],
    config: ReplayConfig,
) -> ReplayResult:
    """用离线快照回放单个二元市场的 P1 信号。

    每个 YES 盘口快照只能看到 `recv_ts` 不晚于它的 NO 盘口和 Binance tick；
    因此该函数不会用未来数据补齐信号。
    """

    signals: list[ArbSignal] = []
    skipped_events = 0
    sorted_yes = sorted(yes_books, key=lambda event: event.recv_ts)
    sorted_no = sorted(no_books, key=lambda event: event.recv_ts)
    sorted_ticks = sorted(ticks, key=lambda event: event.recv_ts)

    for yes_book in sorted_yes:
        no_book = _latest_not_after(sorted_no, yes_book.recv_ts)
        latest_tick = _latest_not_after(sorted_ticks, yes_book.recv_ts)
        if no_book is None or latest_tick is None:
            skipped_events += 1
            continue

        wash_suspect = (
            assess_order_book_wash(yes_book).is_suspect
            or assess_order_book_wash(no_book).is_suspect
        )
        exit_liquidity_ok = is_exit_liquidity_ok(
            yes_book,
            config.liquidity,
        ) and is_exit_liquidity_ok(no_book, config.liquidity)

        signals.extend(
            find_structural_signals(
                market=market,
                yes_book=yes_book,
                no_book=no_book,
                config=config.structural,
                wash_suspect=wash_suspect,
                exit_liquidity_ok=exit_liquidity_ok,
            )
        )

        fair_value = estimate_threshold_probability(
            condition_id=market.condition_id,
            tick=latest_tick,
            threshold_price=config.threshold_price,
            expiry=config.expiry,
            annualized_vol=config.annualized_vol,
        )
        signals.extend(
            find_latency_signals(
                market=market,
                order_book=yes_book,
                fair_value=fair_value,
                config=config.latency,
                wash_suspect=wash_suspect,
                exit_liquidity_ok=exit_liquidity_ok,
            )
        )

    return ReplayResult(signals=signals, skipped_events=skipped_events)

