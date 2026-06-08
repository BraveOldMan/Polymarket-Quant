"""只读结算接口。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SettlementMechanism(StrEnum):
    """结算机制族。"""

    CTF = "ctf"
    NEGRISK = "negrisk"
    UMA = "uma"


class SettlementStatus(StrEnum):
    """结算请求状态。"""

    DISABLED = "disabled"


class SettlementIntent(BaseModel):
    """未来链上结算意图的幂等记录。"""

    intent_id: str = Field(min_length=1)
    condition_id: str = Field(min_length=1)
    mechanism: SettlementMechanism
    nonce_key: str = Field(min_length=1)


class SettlementResult(BaseModel):
    """结算接口返回值。"""

    status: SettlementStatus
    reason: str
    intent_id: str


class ReadOnlySettlementClient:
    """P1 只读结算客户端。

    该客户端只接受意图记录并返回 disabled，不访问钱包、不签名、不广播。
    """

    def submit_intent(self, intent: SettlementIntent) -> SettlementResult:
        """拒绝任何结算意图。"""

        return SettlementResult(
            status=SettlementStatus.DISABLED,
            reason="read_only_stage",
            intent_id=intent.intent_id,
        )

