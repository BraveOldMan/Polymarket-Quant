"""推理层契约。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ReasoningStatus(StrEnum):
    """推理结论状态。"""

    PASS = "pass"
    REJECT = "reject"
    NEEDS_REVIEW = "needs_review"


class EvidenceBundle(BaseModel):
    """注入推理层的已校验证据集合。"""

    signal_ids: list[str] = Field(default_factory=list)
    input_refs: list[str] = Field(default_factory=list)
    untrusted_text: list[str] = Field(default_factory=list)


class ReasoningVerdict(BaseModel):
    """推理层输出摘要。

    首轮不调用 LLM；该模型只定义未来 MCP 注入后的结构化输出边界。
    """

    status: ReasoningStatus
    confidence: float = Field(ge=0.0, le=1.0)
    rationale_summary: str
    evidence_refs: list[str] = Field(default_factory=list)

