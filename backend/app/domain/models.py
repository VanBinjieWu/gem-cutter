from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.utcnow()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class ProjectStatus(str, Enum):
    CREATED = "created"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunStage(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    COLLECTING_SIGNALS = "collecting_signals"
    NORMALIZING_EVIDENCE = "normalizing_evidence"
    ENRICHING_EVIDENCE = "enriching_evidence"
    CLUSTERING_EVIDENCE = "clustering_evidence"
    SCORING = "scoring"
    GATE_REVIEW = "gate_review"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class EvidenceStatus(str, Enum):
    CANDIDATE = "candidate"
    VALID = "valid"
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    FAILED = "failed"
    MANUALLY_ADDED = "manually_added"
    LOW_CONFIDENCE = "low_confidence"


class GateAction(str, Enum):
    GO = "go"
    CONDITIONAL_GO = "conditional_go"
    HOLD = "hold"
    STOP = "stop"


class ReportType(str, Enum):
    EVALUATION = "evaluation"
    PRD = "prd"


class Dimension(str, Enum):
    TREND_STRENGTH = "trend_strength"
    USER_PAIN = "user_pain"
    MONETIZATION = "monetization"
    COMPETITION_GAP = "competition_gap"
    EXECUTION_FEASIBILITY = "execution_feasibility"
    PUBLIC_OPINION_RISK = "public_opinion_risk"
    TIMING_WINDOW = "timing_window"


DIMENSION_WEIGHTS: Dict[str, float] = {
    Dimension.TREND_STRENGTH.value: 0.20,
    Dimension.USER_PAIN.value: 0.18,
    Dimension.MONETIZATION.value: 0.18,
    Dimension.COMPETITION_GAP.value: 0.14,
    Dimension.EXECUTION_FEASIBILITY.value: 0.12,
    Dimension.PUBLIC_OPINION_RISK.value: 0.10,
    Dimension.TIMING_WINDOW.value: 0.08,
}


class DomainModel(BaseModel):
    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda value: value.isoformat()}


class OpportunityProject(DomainModel):
    id: str = Field(default_factory=lambda: new_id("proj"))
    topic_id: str = Field(default_factory=lambda: new_id("topic"))
    title: str
    input_topic: str
    target_market: Optional[str] = None
    target_user_hint: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    status: ProjectStatus = ProjectStatus.CREATED
    latest_evaluation_run_id: Optional[str] = None
    latest_report_id: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class EvaluationRun(DomainModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    project_id: str
    topic_id: str
    status: RunStatus = RunStatus.PENDING
    stage: RunStage = RunStage.PENDING
    progress: int = 0
    message: str = "pending"
    plan: Dict[str, Any] = Field(default_factory=dict)
    budget: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class RawSignal(DomainModel):
    id: str = Field(default_factory=lambda: new_id("sig"))
    evaluation_run_id: str
    source_adapter: str
    source_platform: str
    source_type: str
    dimension: str
    query: str
    url: Optional[str] = None
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime = Field(default_factory=utc_now)
    normalization_status: str = "pending"
    error: Optional[str] = None


class EvidenceItem(DomainModel):
    id: str = Field(default_factory=lambda: new_id("ev"))
    evaluation_run_id: str
    project_id: str
    raw_signal_id: Optional[str] = None
    cluster_id: Optional[str] = None
    dimension: str
    title: str
    content: str
    summary: str
    url: Optional[str] = None
    source_platform: str
    source_type: str
    content_type: str = "article"
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=utc_now)
    engagement_metrics: Dict[str, float] = Field(default_factory=dict)
    hotness_score: float = 0.0
    sentiment_label: str = "unknown"
    sentiment_score: float = 0.0
    stance_label: str = "unknown"
    credibility_score: float = 0.0
    freshness_score: float = 0.0
    relevance_score: float = 0.0
    dedupe_hash: str
    status: EvidenceStatus = EvidenceStatus.CANDIDATE
    tags: List[str] = Field(default_factory=list)


class EvidenceCluster(DomainModel):
    id: str = Field(default_factory=lambda: new_id("cluster"))
    evaluation_run_id: str
    dimension: str
    label: str
    summary: str
    representative_evidence_ids: List[str] = Field(default_factory=list)
    evidence_count: int = 0
    source_diversity: float = 0.0
    avg_hotness_score: float = 0.0
    avg_sentiment_score: float = 0.0
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None


class ScoreLedger(DomainModel):
    id: str = Field(default_factory=lambda: new_id("score"))
    evaluation_run_id: str
    dimension: str
    score: float
    confidence: float
    weight: float
    rationale: str
    positive_evidence_ids: List[str] = Field(default_factory=list)
    negative_evidence_ids: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class GateDecision(DomainModel):
    id: str = Field(default_factory=lambda: new_id("gate"))
    evaluation_run_id: str
    project_id: str
    action: GateAction
    total_score: float
    confidence: float
    reason: str
    next_steps: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class EvaluationReport(DomainModel):
    id: str = Field(default_factory=lambda: new_id("report"))
    evaluation_run_id: str
    project_id: str
    report_type: ReportType
    title: str
    markdown_path: str
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(default_factory=list)
    status: str = "final"
    created_at: datetime = Field(default_factory=utc_now)


class LLMCallLog(DomainModel):
    id: str = Field(default_factory=lambda: new_id("llmlog"))
    evaluation_run_id: str
    provider: str
    model: str
    purpose: str
    dimension: Optional[str] = None
    query: Optional[str] = None
    status: str = "running"
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    event_count: int = 0
    reasoning_text: str = ""
    output_text: str = ""
    raw_events: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class EventRecord(DomainModel):
    id: str = Field(default_factory=lambda: new_id("evt"))
    evaluation_run_id: str
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class StoreData(DomainModel):
    projects: Dict[str, OpportunityProject] = Field(default_factory=dict)
    runs: Dict[str, EvaluationRun] = Field(default_factory=dict)
    raw_signals: Dict[str, RawSignal] = Field(default_factory=dict)
    evidence_items: Dict[str, EvidenceItem] = Field(default_factory=dict)
    evidence_clusters: Dict[str, EvidenceCluster] = Field(default_factory=dict)
    score_ledgers: Dict[str, ScoreLedger] = Field(default_factory=dict)
    gate_decisions: Dict[str, GateDecision] = Field(default_factory=dict)
    reports: Dict[str, EvaluationReport] = Field(default_factory=dict)
    llm_call_logs: Dict[str, LLMCallLog] = Field(default_factory=dict)
    events: Dict[str, EventRecord] = Field(default_factory=dict)
