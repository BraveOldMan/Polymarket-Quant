"""策略①单条件结构套利信号。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from polymarket_quant.data.schemas import (
    ArbSignal,
    Market,
    OrderBookSnapshot,
    Side,
    SignalLeg,
    SignalStrategy,
)
from polymarket_quant.data.signals.common import bps_to_probability


@dataclass(frozen=True)
class StructuralConfig:
    """结构套利信号参数。"""

    min_edge: Decimal = Decimal("0.005")
    cost_bps: Decimal = Decimal("100")
    target_size: Decimal = Decimal("1")
    include_rejected: bool = False


def find_structural_signals(
    market: Market,
    yes_book: OrderBookSnapshot,
    no_book: OrderBookSnapshot,
    config: StructuralConfig | None = None,
    wash_suspect: bool = False,
    exit_liquidity_ok: bool = True,
) -> list[ArbSignal]:
    """计算策略① `YES+NO<1-cost` 的只读观察信号。

    该函数只识别买齐完整套件的低估机会，不实现卖出、链上操作或任何
    下单路径。双腿规模取两侧最优卖档与配置目标规模的最小值。
    """

    cfg = config or StructuralConfig()
    if (wash_suspect or not exit_liquidity_ok) and not cfg.include_rejected:
        return []

    try:
        yes_ask = yes_book.best_ask
        no_ask = no_book.best_ask
    except ValueError:
        return []

    size = min(cfg.target_size, yes_ask.size, no_ask.size)
    if size <= 0:
        return []

    combined_cost = yes_ask.price + no_ask.price
    edge = Decimal("1") - combined_cost
    edge_after_cost = edge - bps_to_probability(cfg.cost_bps)
    if edge_after_cost < cfg.min_edge:
        return []

    return [
        ArbSignal(
            strategy=SignalStrategy.SINGLE,
            condition_id=market.condition_id,
            side=Side.YES,
            market_prob=combined_cost,
            fair_prob=Decimal("1"),
            edge=edge,
            edge_after_cost=edge_after_cost,
            confidence=Decimal("1"),
            legs=[
                SignalLeg(
                    token_id=market.token_id_yes,
                    side=Side.YES,
                    price=yes_ask.price,
                    size=size,
                    role="buy_complete_set",
                ),
                SignalLeg(
                    token_id=market.token_id_no,
                    side=Side.NO,
                    price=no_ask.price,
                    size=size,
                    role="buy_complete_set",
                ),
            ],
            exit_liquidity_ok=exit_liquidity_ok,
            wash_suspect=wash_suspect,
            inputs_ref=[yes_book.event_ref, no_book.event_ref],
            ts=max(yes_book.recv_ts, no_book.recv_ts),
        )
    ]

