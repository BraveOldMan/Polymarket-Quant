"""信号计算通用工具。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal


def bps_to_probability(cost_bps: Decimal) -> Decimal:
    """把 bps 成本转换为概率价差口径。"""

    return cost_bps / Decimal("10000")


def clamp_probability(value: Decimal) -> Decimal:
    """把数值裁剪到概率区间。"""

    return max(Decimal("0"), min(Decimal("1"), value))


def recv_delta_ms(left: datetime, right: datetime) -> int:
    """计算两个接收时间戳的绝对毫秒差。"""

    return int(abs((left - right).total_seconds()) * 1000)

