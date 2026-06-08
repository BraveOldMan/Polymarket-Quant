"""策略④的公允概率估计。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from math import erf, log, sqrt

from polymarket_quant.data.schemas import FairValueEstimate, PriceTick
from polymarket_quant.data.signals.common import clamp_probability


def _normal_cdf(value: float) -> float:
    """标准正态分布函数。"""

    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def estimate_threshold_probability(
    condition_id: str,
    tick: PriceTick,
    threshold_price: Decimal,
    expiry: datetime,
    annualized_vol: Decimal,
    confidence_width: Decimal = Decimal("0.05"),
) -> FairValueEstimate:
    """用 Binance 价格估计阈值型市场的超过概率。

    输入时间口径：只使用 `tick.event_ts` 及其之前可得的信息；`tick.recv_ts`
    作为输出时间戳，供延时套利做跨源对齐。模型为零漂移对数正态近似，
    仅用于 P1 离线信号验证，不构成可实盘概率模型。
    """

    if threshold_price <= 0:
        raise ValueError("threshold_price 必须为正")
    if annualized_vol <= 0:
        raise ValueError("annualized_vol 必须为正")

    seconds_to_expiry = (expiry - tick.event_ts).total_seconds()
    if seconds_to_expiry <= 0:
        fair_prob = Decimal("1") if tick.price > threshold_price else Decimal("0")
    else:
        years_to_expiry = seconds_to_expiry / (365.0 * 24.0 * 60.0 * 60.0)
        sigma = float(annualized_vol)
        spot = float(tick.price)
        strike = float(threshold_price)
        std = sigma * sqrt(years_to_expiry)
        if std == 0:
            probability = 1.0 if spot > strike else 0.0
        else:
            z_score = (log(strike / spot) + 0.5 * sigma * sigma * years_to_expiry) / std
            probability = 1.0 - _normal_cdf(z_score)
        fair_prob = clamp_probability(Decimal(str(probability)))

    conf_lo = clamp_probability(fair_prob - confidence_width)
    conf_hi = clamp_probability(fair_prob + confidence_width)
    return FairValueEstimate(
        condition_id=condition_id,
        fair_prob=fair_prob,
        conf_lo=conf_lo,
        conf_hi=conf_hi,
        basis="latency_arb",
        inputs_ref=[tick.event_ref],
        ts=tick.recv_ts,
    )

