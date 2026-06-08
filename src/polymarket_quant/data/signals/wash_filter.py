"""洗盘与自成交启发式过滤。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from polymarket_quant.data.schemas import OrderBookSnapshot


@dataclass(frozen=True)
class WashFilterConfig:
    """洗盘检测参数。"""

    extreme_low: Decimal = Decimal("0.04")
    extreme_high: Decimal = Decimal("0.96")
    min_extreme_size: Decimal = Decimal("100")


@dataclass(frozen=True)
class WashAssessment:
    """洗盘检测结果。"""

    is_suspect: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


def assess_order_book_wash(
    snapshot: OrderBookSnapshot,
    config: WashFilterConfig | None = None,
) -> WashAssessment:
    """基于订单簿异常形态识别疑似洗盘市场。

    首轮没有地址成交图，因此只做保守启发式：极端高买价与极端低卖价
    同时出现且规模较大时，标记为疑似自挂自接。
    """

    cfg = config or WashFilterConfig()
    reasons: list[str] = []
    try:
        best_bid = snapshot.best_bid
        best_ask = snapshot.best_ask
    except ValueError:
        return WashAssessment(is_suspect=False)

    extreme_cross = (
        best_bid.price >= cfg.extreme_high
        and best_ask.price <= cfg.extreme_low
        and best_bid.size >= cfg.min_extreme_size
        and best_ask.size >= cfg.min_extreme_size
    )
    if extreme_cross:
        reasons.append("extreme_crossed_book")

    return WashAssessment(is_suspect=bool(reasons), reasons=tuple(reasons))

