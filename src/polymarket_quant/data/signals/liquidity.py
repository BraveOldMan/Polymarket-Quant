"""出场流动性预检。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from polymarket_quant.data.schemas import OrderBookSnapshot
from polymarket_quant.data.signals.common import bps_to_probability


@dataclass(frozen=True)
class LiquidityConfig:
    """出场流动性检查参数。"""

    target_size: Decimal = Decimal("1")
    max_slippage_bps: Decimal = Decimal("250")


def available_exit_depth(
    snapshot: OrderBookSnapshot,
    max_slippage_bps: Decimal,
) -> Decimal:
    """估算可接受滑点内可卖出的 bid 深度。"""

    if not snapshot.bids:
        return Decimal("0")
    best_bid = snapshot.best_bid.price
    min_acceptable_bid = best_bid * (Decimal("1") - bps_to_probability(max_slippage_bps))
    return sum(
        level.size
        for level in snapshot.bids
        if level.price >= min_acceptable_bid
    )


def is_exit_liquidity_ok(
    snapshot: OrderBookSnapshot,
    config: LiquidityConfig | None = None,
) -> bool:
    """判断目标规模是否具备可接受出场深度。"""

    cfg = config or LiquidityConfig()
    return available_exit_depth(snapshot, cfg.max_slippage_bps) >= cfg.target_size

