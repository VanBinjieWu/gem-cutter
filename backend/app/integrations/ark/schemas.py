from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


SourceType = Literal["web", "news", "community", "official", "report", "store", "manual", "unknown"]
SentimentHint = Literal["positive", "neutral", "negative", "mixed", "unknown"]


class ArkEvidenceCandidate(BaseModel):
    title: str
    url: Optional[str] = None
    source_platform: str = "web"
    source_type: SourceType = "web"
    published_at: Optional[str] = None
    content: str
    summary: str
    supported_claims: List[str] = Field(default_factory=list)
    credibility_hint: float = Field(default=0.5, ge=0, le=1)
    relevance_hint: float = Field(default=0.5, ge=0, le=1)
    hotness_hint: float = Field(default=0.0, ge=0, le=1)
    sentiment_hint: SentimentHint = "unknown"
    risk_flags: List[str] = Field(default_factory=list)


class ArkEvidenceSearchResult(BaseModel):
    items: List[ArkEvidenceCandidate] = Field(default_factory=list)
    search_summary: str = ""
    missing_evidence: List[str] = Field(default_factory=list)


class ArkScoreDraftItem(BaseModel):
    dimension: str
    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    rationale: str
    positive_evidence_ids: List[str] = Field(default_factory=list)
    negative_evidence_ids: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class ArkScoreDraftResult(BaseModel):
    scores: List[ArkScoreDraftItem] = Field(default_factory=list)
    cross_dimension_risks: List[str] = Field(default_factory=list)
    recommended_gate: Literal["go", "conditional_go", "hold", "stop"] = "hold"
    gate_reason: str = ""


class ArkPrdFeature(BaseModel):
    title: str
    rationale: str
    user_stories: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class ArkPrdDraftResult(BaseModel):
    title: str
    executive_summary: str
    target_users: List[str] = Field(default_factory=list)
    problem_statement: str
    value_proposition: str
    goals: List[str] = Field(default_factory=list)
    non_goals: List[str] = Field(default_factory=list)
    mvp_scope: List[ArkPrdFeature] = Field(default_factory=list)
    user_journey: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    launch_plan: List[str] = Field(default_factory=list)
    risks_and_mitigations: List[str] = Field(default_factory=list)
    open_assumptions: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


def evidence_search_json_schema() -> Dict[str, Any]:
    return ArkEvidenceSearchResult.schema()


def prd_draft_json_schema() -> Dict[str, Any]:
    return ArkPrdDraftResult.schema()
