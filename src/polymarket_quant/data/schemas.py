"""数据层统一契约。

所有外部数据进入信号层前都必须先通过这些模型校验。自由文本字段只保证
格式正确，不代表内容可信；注入下游 LLM 前仍需做内容与指令分离。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Side(StrEnum):
    """预测市场二元方向。"""

    YES = "YES"
    NO = "NO"


class MarketType(StrEnum):
    """Binance 行情市场类型。"""

    SPOT = "spot"
    PERP = "perp"


class SignalStrategy(StrEnum):
    """信号来源策略族。"""

    SINGLE = "single"
    LATENCY = "latency"
    MULTI = "multi"
    SEMANTIC = "semantic"
    TIME_DECAY = "time_decay"
    COPY = "copy"


class StrictSchema(BaseModel):
    """项目内 pydantic 模型基类。"""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Market(StrictSchema):
    """Polymarket 市场元数据。

    输入来源为 Gamma/Data API。`question` 是不可信自由文本，不能作为工具
    指令或交易触发器直接传给 LLM。
    """

    condition_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    token_id_yes: str = Field(min_length=1)
    token_id_no: str = Field(min_length=1)
    category: str = Field(min_length=1)
    end_date: datetime | None
    active: bool

    def token_id_for(self, side: Side) -> str:
        """返回指定方向对应的 token id。"""

        return self.token_id_yes if side is Side.YES else self.token_id_no


class OrderBookLevel(StrictSchema):
    """订单簿一档价格与数量。"""

    price: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    size: Decimal = Field(ge=Decimal("0"))


class OrderBookSnapshot(StrictSchema):
    """Polymarket 单个 token 的订单簿快照。

    `event_ts` 是交易所或数据源时间，`recv_ts` 是本地接收时间。延时套利
    只使用 `recv_ts` 做跨源对齐，避免外部时钟漂移。
    """

    token_id: str = Field(min_length=1)
    bids: list[OrderBookLevel] = Field(default_factory=list)
    asks: list[OrderBookLevel] = Field(default_factory=list)
    event_ts: datetime
    recv_ts: datetime

    @property
    def best_bid(self) -> OrderBookLevel:
        """返回最高买价；空盘口显式失败。"""

        if not self.bids:
            raise ValueError("订单簿缺少 bids，无法计算 best_bid")
        return max(self.bids, key=lambda level: level.price)

    @property
    def best_ask(self) -> OrderBookLevel:
        """返回最低卖价；空盘口显式失败。"""

        if not self.asks:
            raise ValueError("订单簿缺少 asks，无法计算 best_ask")
        return min(self.asks, key=lambda level: level.price)

    @property
    def mid(self) -> Decimal:
        """返回中间价，作为 Polymarket 隐含概率。"""

        return (self.best_bid.price + self.best_ask.price) / Decimal("2")

    @property
    def event_ref(self) -> str:
        """生成可追溯输入引用。"""

        return f"orderbook:{self.token_id}:{self.recv_ts.isoformat()}"


class PriceTick(StrictSchema):
    """Binance 行情 tick。

    用作策略④延时套利的公允概率锚点。`recv_ts` 是跨源对齐主时间。
    """

    symbol: str = Field(min_length=1)
    market_type: MarketType
    price: Decimal = Field(gt=Decimal("0"))
    event_ts: datetime
    recv_ts: datetime

    @property
    def event_ref(self) -> str:
        """生成可追溯输入引用。"""

        return f"tick:{self.symbol}:{self.recv_ts.isoformat()}"


class ChainEvent(StrictSchema):
    """Polygon 链上公开事件。"""

    tx_hash: str = Field(min_length=1)
    from_addr: str = Field(min_length=1)
    to_addr: str = Field(min_length=1)
    token: str = Field(min_length=1)
    amount: Decimal = Field(ge=Decimal("0"))
    block_number: int = Field(ge=0)
    event_ts: datetime


class MacroSignal(StrictSchema):
    """OpenBB 宏观或基本面信号。"""

    indicator: str = Field(min_length=1)
    value: Decimal
    released_at: datetime
    provider: str = Field(min_length=1)


class FairValueEstimate(StrictSchema):
    """信号层对某市场的公允概率估计。

    `inputs_ref` 必须保留参与估计的输入事件引用，便于回放和审计。
    """

    condition_id: str = Field(min_length=1)
    fair_prob: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    conf_lo: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    conf_hi: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    basis: str = Field(min_length=1)
    inputs_ref: list[str] = Field(default_factory=list)
    ts: datetime

    @model_validator(mode="after")
    def validate_interval(self) -> FairValueEstimate:
        """校验置信区间包住点估计。"""

        if self.conf_lo > self.conf_hi:
            raise ValueError("conf_lo 不能大于 conf_hi")
        if not self.conf_lo <= self.fair_prob <= self.conf_hi:
            raise ValueError("fair_prob 必须位于置信区间内")
        return self


class SignalLeg(StrictSchema):
    """多腿策略中的单腿报价。"""

    token_id: str = Field(min_length=1)
    side: Side
    price: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    size: Decimal = Field(gt=Decimal("0"))
    role: str = Field(min_length=1)


class ArbSignal(StrictSchema):
    """信号层套利价差信号。

    首轮只读阶段的信号只表示研究观察，不代表下单指令。
    """

    strategy: SignalStrategy
    condition_id: str = Field(min_length=1)
    side: Side
    market_prob: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    fair_prob: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    edge: Decimal
    edge_after_cost: Decimal
    confidence: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    legs: list[SignalLeg] = Field(default_factory=list)
    exit_liquidity_ok: bool = True
    wash_suspect: bool = False
    inputs_ref: list[str] = Field(default_factory=list)
    ts: datetime


class MarketGroup(StrictSchema):
    """互斥市场组，用于后续策略②。"""

    event_id: str = Field(min_length=1)
    condition_ids: list[str] = Field(min_length=1)
    yes_sum: Decimal = Field(ge=Decimal("0"))
    is_exhaustive: bool
    is_mutually_exclusive: bool

    @property
    def is_valid_neg_risk_group(self) -> bool:
        """判断是否具备互斥且穷尽的基础条件。"""

        return self.is_exhaustive and self.is_mutually_exclusive


class SemanticLink(StrictSchema):
    """跨市场语义等价映射，用于后续策略③。"""

    primary_condition_id: str = Field(min_length=1)
    equivalent_basket: list[str] = Field(min_length=1)
    equivalence_conf: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    verified_by: str = Field(min_length=1)

    @property
    def is_auto_allowed(self) -> bool:
        """纯 LLM 验证不能自动放行。"""

        return self.verified_by in {"rule", "human"}


class ExpiringTarget(StrictSchema):
    """临到期极端目标，用于后续高风险策略⑤。"""

    condition_id: str = Field(min_length=1)
    end_date: datetime
    days_to_expiry: int = Field(ge=0)
    no_prob: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    is_extreme_target: bool
    settlement_rule: str = Field(min_length=1)


class WalletProfile(StrictSchema):
    """公开链上钱包画像，用于后续高风险策略⑥。"""

    address: str = Field(min_length=1)
    trades: int = Field(ge=0)
    win_rate: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    realized_pnl: Decimal
    first_active: datetime
    insider_suspect: bool


JsonObject = dict[str, Any]

