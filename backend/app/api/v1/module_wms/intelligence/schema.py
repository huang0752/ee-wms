from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WmsRiskLevel(StrEnum):
    normal = "normal"
    warning = "warning"
    critical = "critical"


class WmsIntelligenceSource(StrEnum):
    ai = "ai"
    rule_fallback = "rule_fallback"


class WmsIntelligenceAction(BaseModel):
    label: str = Field(..., min_length=1, max_length=80)
    route: str | None = Field(None, max_length=200)
    permission: str | None = Field(None, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)


class WmsIntelligenceSummaryOut(BaseModel):
    title: str
    summary: str
    risk_level: WmsRiskLevel = WmsRiskLevel.normal
    source: WmsIntelligenceSource = WmsIntelligenceSource.rule_fallback
    bullets: list[str] = Field(default_factory=list)
    actions: list[WmsIntelligenceAction] = Field(default_factory=list)


class WmsIntelligenceDraft(BaseModel):
    summary: str = Field(..., min_length=1, max_length=300)
    bullets: list[str] = Field(default_factory=list, max_length=5)


class WmsWarningAdviceOut(BaseModel):
    warning_id: int
    warning_type: str
    risk_level: WmsRiskLevel
    reason: str
    advice: str
    source: WmsIntelligenceSource
    actions: list[WmsIntelligenceAction] = Field(default_factory=list)


class WmsOutboundExplainRequest(BaseModel):
    material_id: int = Field(..., ge=1)
    warehouse_id: int | None = Field(None, ge=1)
    location_id: int | None = Field(None, ge=1)
    required_qty: str | None = None


class WmsOutboundCandidateScore(BaseModel):
    balance_id: int
    material_id: int
    warehouse_id: int
    location_id: int | None = None
    batch_no: str | None = None
    available_qty: str
    score: int
    rule_reasons: list[str] = Field(default_factory=list)


class WmsOutboundExplainOut(BaseModel):
    material_id: int
    source: WmsIntelligenceSource
    summary: str
    candidates: list[WmsOutboundCandidateScore]
