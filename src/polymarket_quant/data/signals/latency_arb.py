"""策略④延时套利信号。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from polymarket_quant.data.schemas import (
    ArbSignal,
    FairValueEstimate,
    Market,
    OrderBookSnapshot,
    Side,
    SignalStrategy,
)
from polymarket_quant.data.signals.common import bps_to_probability, recv_delta_ms


@dataclass(frozen=True)
class LatencyConfig:
    """延时套利信号参数。"""

    delta_max_ms: int = 250
    min_edge: Decimal = Decimal("0.005")
    cost_bps: Decimal = Decimal("100")
    include_rejected: bool = False


def find_latency_signals(
    market: Market,
    order_book: OrderBookSnapshot,
    fair_value: FairValueEstimate,
    config: LatencyConfig | None = None,
    wash_suspect: bool = False,
    exit_liquidity_ok: bool = True,
) -> list[ArbSignal]:
    """计算策略④延时价差信号。

    只有当 Polymarket 与 Binance 的 `recv_ts` 差值不超过 `delta_max_ms`、
    扣成本后边际达标且置信区间不跨越市价时才输出信号。
    """

    cfg = config or LatencyConfig()
    if (wash_suspect or not exit_liquidity_ok) and not cfg.include_rejected:
        return []
    if recv_delta_ms(order_book.recv_ts, fair_value.ts) > cfg.delta_max_ms:
        return []

    try:
        market_prob = order_book.mid
    except ValueError:
        return []

    fair_prob = fair_value.fair_prob
    if fair_prob >= market_prob:
        side = Side.YES
        edge = fair_prob - market_prob
        interval_clears_market = fair_value.conf_lo > market_prob
    else:
        side = Side.NO
        edge = market_prob - fair_prob
        interval_clears_market = fair_value.conf_hi < market_prob

    edge_after_cost = edge - bps_to_probability(cfg.cost_bps)
    if edge_after_cost < cfg.min_edge or not interval_clears_market:
        return []

    interval_width = fair_value.conf_hi - fair_value.conf_lo
    confidence = max(Decimal("0"), Decimal("1") - interval_width)
    return [
        ArbSignal(
            strategy=SignalStrategy.LATENCY,
            condition_id=market.condition_id,
            side=side,
            market_prob=market_prob,
            fair_prob=fair_prob,
            edge=edge,
            edge_after_cost=edge_after_cost,
            confidence=confidence,
            exit_liquidity_ok=exit_liquidity_ok,
            wash_suspect=wash_suspect,
            inputs_ref=[order_book.event_ref, *fair_value.inputs_ref],
            ts=order_book.recv_ts,
        )
    ]

