from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional, Protocol

from .models import (
    EvaluationReport,
    EvaluationRun,
    EventRecord,
    EvidenceCluster,
    EvidenceItem,
    GateDecision,
    LLMCallLog,
    OpportunityProject,
    RawSignal,
    ScoreLedger,
    utc_now,
)


class StoreProtocol(Protocol):
    live_llm_call_logs: Dict[str, LLMCallLog]

    def add_project(self, project: OpportunityProject) -> OpportunityProject: ...
    def get_project(self, project_id: str) -> Optional[OpportunityProject]: ...
    def list_projects(self) -> List[OpportunityProject]: ...
    def update_project(self, project: OpportunityProject) -> OpportunityProject: ...
    def add_run(self, run: EvaluationRun) -> EvaluationRun: ...
    def get_run(self, run_id: str) -> Optional[EvaluationRun]: ...
    def update_run(self, run: EvaluationRun) -> EvaluationRun: ...
    def add_raw_signals(self, signals: Iterable[RawSignal]) -> List[RawSignal]: ...
    def list_raw_signals(self, run_id: str) -> List[RawSignal]: ...
    def update_raw_signal(self, signal: RawSignal) -> RawSignal: ...
    def add_evidence_items(self, items: Iterable[EvidenceItem]) -> List[EvidenceItem]: ...
    def update_evidence_item(self, item: EvidenceItem) -> EvidenceItem: ...
    def get_evidence_item(self, evidence_id: str) -> Optional[EvidenceItem]: ...
    def list_evidence(self, run_id: str) -> List[EvidenceItem]: ...
    def add_clusters(self, clusters: Iterable[EvidenceCluster]) -> List[EvidenceCluster]: ...
    def list_clusters(self, run_id: str) -> List[EvidenceCluster]: ...
    def add_scores(self, scores: Iterable[ScoreLedger]) -> List[ScoreLedger]: ...
    def list_scores(self, run_id: str) -> List[ScoreLedger]: ...
    def add_gate_decision(self, decision: GateDecision) -> GateDecision: ...
    def get_latest_gate_decision(self, run_id: str) -> Optional[GateDecision]: ...
    def add_report(self, report: EvaluationReport) -> EvaluationReport: ...
    def get_report(self, report_id: str) -> Optional[EvaluationReport]: ...
    def list_reports(self, run_id: str) -> List[EvaluationReport]: ...
    def save_report_markdown(self, report_id: str, markdown: str) -> None: ...
    def get_report_markdown(self, report_id: str) -> Optional[str]: ...
    def add_llm_call_log(self, log: LLMCallLog, persist: bool = True) -> LLMCallLog: ...
    def update_llm_call_log(self, log: LLMCallLog, persist: bool = True) -> LLMCallLog: ...
    def list_llm_call_logs(self, run_id: str) -> List[LLMCallLog]: ...
    def add_event(self, event: EventRecord) -> EventRecord: ...
    def list_events(self, run_id: str) -> List[EventRecord]: ...


def _dt(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_value(value: Optional[str], default: Any) -> Any:
    if value is None:
        return default
    return json.loads(value)


class SQLiteStore:
    def __init__(self, path: str | Path = "data/gem_cutter.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self.live_llm_call_logs: Dict[str, LLMCallLog] = {}
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(
                """
                DROP TABLE IF EXISTS domain_entities;
                DROP TABLE IF EXISTS report_markdowns;

                CREATE TABLE IF NOT EXISTS opportunity_projects (
                    id TEXT PRIMARY KEY,
                    topic_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    input_topic TEXT NOT NULL,
                    target_market TEXT,
                    target_user_hint TEXT,
                    constraints_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    latest_evaluation_run_id TEXT,
                    latest_report_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    topic_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    budget_json TEXT NOT NULL,
                    error TEXT,
                    started_at TEXT,
                    finished_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_evaluation_runs_project
                    ON evaluation_runs(project_id);

                CREATE TABLE IF NOT EXISTS raw_signals (
                    id TEXT PRIMARY KEY,
                    evaluation_run_id TEXT NOT NULL,
                    source_adapter TEXT NOT NULL,
                    source_platform TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    query TEXT NOT NULL,
                    url TEXT,
                    raw_payload_json TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    normalization_status TEXT NOT NULL,
                    error TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_raw_signals_run
                    ON raw_signals(evaluation_run_id, fetched_at, id);

                CREATE TABLE IF NOT EXISTS evidence_items (
                    id TEXT PRIMARY KEY,
                    evaluation_run_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    raw_signal_id TEXT,
                    cluster_id TEXT,
                    dimension TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    url TEXT,
                    source_platform TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    author TEXT,
                    published_at TEXT,
                    fetched_at TEXT NOT NULL,
                    engagement_metrics_json TEXT NOT NULL,
                    hotness_score REAL NOT NULL,
                    sentiment_label TEXT NOT NULL,
                    sentiment_score REAL NOT NULL,
                    stance_label TEXT NOT NULL,
                    credibility_score REAL NOT NULL,
                    freshness_score REAL NOT NULL,
                    relevance_score REAL NOT NULL,
                    dedupe_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    tags_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_evidence_items_run
                    ON evidence_items(evaluation_run_id, fetched_at, id);
                CREATE INDEX IF NOT EXISTS idx_evidence_items_project
                    ON evidence_items(project_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_items_dedupe
                    ON evidence_items(evaluation_run_id, dedupe_hash);

                CREATE TABLE IF NOT EXISTS evidence_clusters (
                    id TEXT PRIMARY KEY,
                    evaluation_run_id TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    label TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    representative_evidence_ids_json TEXT NOT NULL,
                    evidence_count INTEGER NOT NULL,
                    source_diversity REAL NOT NULL,
                    avg_hotness_score REAL NOT NULL,
                    avg_sentiment_score REAL NOT NULL,
                    time_range_start TEXT,
                    time_range_end TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_evidence_clusters_run
                    ON evidence_clusters(evaluation_run_id, id);

                CREATE TABLE IF NOT EXISTS score_ledgers (
                    id TEXT PRIMARY KEY,
                    evaluation_run_id TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    weight REAL NOT NULL,
                    rationale TEXT NOT NULL,
                    positive_evidence_ids_json TEXT NOT NULL,
                    negative_evidence_ids_json TEXT NOT NULL,
                    missing_evidence_json TEXT NOT NULL,
                    assumptions_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_score_ledgers_run
                    ON score_ledgers(evaluation_run_id, created_at, id);

                CREATE TABLE IF NOT EXISTS gate_decisions (
                    id TEXT PRIMARY KEY,
                    evaluation_run_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    total_score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    reason TEXT NOT NULL,
                    next_steps_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_gate_decisions_run
                    ON gate_decisions(evaluation_run_id, created_at);

                CREATE TABLE IF NOT EXISTS evaluation_reports (
                    id TEXT PRIMARY KEY,
                    evaluation_run_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    report_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    markdown_path TEXT NOT NULL,
                    markdown TEXT,
                    structured_data_json TEXT NOT NULL,
                    evidence_refs_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_evaluation_reports_run
                    ON evaluation_reports(evaluation_run_id, created_at);

                CREATE TABLE IF NOT EXISTS llm_call_logs (
                    id TEXT PRIMARY KEY,
                    evaluation_run_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    dimension TEXT,
                    query TEXT,
                    status TEXT NOT NULL,
                    request_payload_json TEXT NOT NULL,
                    event_count INTEGER NOT NULL,
                    reasoning_text TEXT NOT NULL,
                    output_text TEXT NOT NULL,
                    raw_events_json TEXT NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_llm_call_logs_run
                    ON llm_call_logs(evaluation_run_id, created_at);

                CREATE TABLE IF NOT EXISTS event_records (
                    id TEXT PRIMARY KEY,
                    evaluation_run_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_event_records_run
                    ON event_records(evaluation_run_id, created_at);
                """
            )

    def has_data(self) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT 1 FROM opportunity_projects LIMIT 1").fetchone()
        return bool(row)

    def add_project(self, project: OpportunityProject) -> OpportunityProject:
        return self._upsert_project(project)

    def get_project(self, project_id: str) -> Optional[OpportunityProject]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM opportunity_projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        return self._project_from_row(row) if row else None

    def list_projects(self) -> List[OpportunityProject]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM opportunity_projects ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [self._project_from_row(row) for row in rows]

    def update_project(self, project: OpportunityProject) -> OpportunityProject:
        project.updated_at = utc_now()
        return self._upsert_project(project)

    def _upsert_project(self, project: OpportunityProject) -> OpportunityProject:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO opportunity_projects (
                    id, topic_id, title, input_topic, target_market, target_user_hint,
                    constraints_json, status, latest_evaluation_run_id, latest_report_id,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    topic_id = excluded.topic_id,
                    title = excluded.title,
                    input_topic = excluded.input_topic,
                    target_market = excluded.target_market,
                    target_user_hint = excluded.target_user_hint,
                    constraints_json = excluded.constraints_json,
                    status = excluded.status,
                    latest_evaluation_run_id = excluded.latest_evaluation_run_id,
                    latest_report_id = excluded.latest_report_id,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                """,
                (
                    project.id,
                    project.topic_id,
                    project.title,
                    project.input_topic,
                    project.target_market,
                    project.target_user_hint,
                    _json(project.constraints),
                    project.status,
                    project.latest_evaluation_run_id,
                    project.latest_report_id,
                    _dt(project.created_at),
                    _dt(project.updated_at),
                ),
            )
        return project

    def _project_from_row(self, row: sqlite3.Row) -> OpportunityProject:
        return OpportunityProject.parse_obj(
            {
                **dict(row),
                "constraints": _json_value(row["constraints_json"], {}),
            }
        )

    def add_run(self, run: EvaluationRun) -> EvaluationRun:
        return self._upsert_run(run)

    def get_run(self, run_id: str) -> Optional[EvaluationRun]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM evaluation_runs WHERE id = ?", (run_id,)).fetchone()
        return self._run_from_row(row) if row else None

    def update_run(self, run: EvaluationRun) -> EvaluationRun:
        return self._upsert_run(run)

    def _upsert_run(self, run: EvaluationRun) -> EvaluationRun:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO evaluation_runs (
                    id, project_id, topic_id, status, stage, progress, message,
                    plan_json, budget_json, error, started_at, finished_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    project_id = excluded.project_id,
                    topic_id = excluded.topic_id,
                    status = excluded.status,
                    stage = excluded.stage,
                    progress = excluded.progress,
                    message = excluded.message,
                    plan_json = excluded.plan_json,
                    budget_json = excluded.budget_json,
                    error = excluded.error,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at
                """,
                (
                    run.id,
                    run.project_id,
                    run.topic_id,
                    run.status,
                    run.stage,
                    run.progress,
                    run.message,
                    _json(run.plan),
                    _json(run.budget),
                    run.error,
                    _dt(run.started_at),
                    _dt(run.finished_at),
                ),
            )
        return run

    def _run_from_row(self, row: sqlite3.Row) -> EvaluationRun:
        return EvaluationRun.parse_obj(
            {
                **dict(row),
                "plan": _json_value(row["plan_json"], {}),
                "budget": _json_value(row["budget_json"], {}),
            }
        )

    def add_raw_signals(self, signals: Iterable[RawSignal]) -> List[RawSignal]:
        items = list(signals)
        for item in items:
            self.update_raw_signal(item)
        return items

    def list_raw_signals(self, run_id: str) -> List[RawSignal]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM raw_signals
                WHERE evaluation_run_id = ?
                ORDER BY rowid
                """,
                (run_id,),
            ).fetchall()
        return [self._raw_signal_from_row(row) for row in rows]

    def update_raw_signal(self, signal: RawSignal) -> RawSignal:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO raw_signals (
                    id, evaluation_run_id, source_adapter, source_platform, source_type,
                    dimension, query, url, raw_payload_json, fetched_at,
                    normalization_status, error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    evaluation_run_id = excluded.evaluation_run_id,
                    source_adapter = excluded.source_adapter,
                    source_platform = excluded.source_platform,
                    source_type = excluded.source_type,
                    dimension = excluded.dimension,
                    query = excluded.query,
                    url = excluded.url,
                    raw_payload_json = excluded.raw_payload_json,
                    fetched_at = excluded.fetched_at,
                    normalization_status = excluded.normalization_status,
                    error = excluded.error
                """,
                (
                    signal.id,
                    signal.evaluation_run_id,
                    signal.source_adapter,
                    signal.source_platform,
                    signal.source_type,
                    signal.dimension,
                    signal.query,
                    signal.url,
                    _json(signal.raw_payload),
                    _dt(signal.fetched_at),
                    signal.normalization_status,
                    signal.error,
                ),
            )
        return signal

    def _raw_signal_from_row(self, row: sqlite3.Row) -> RawSignal:
        return RawSignal.parse_obj(
            {
                **dict(row),
                "raw_payload": _json_value(row["raw_payload_json"], {}),
            }
        )

    def add_evidence_items(self, items: Iterable[EvidenceItem]) -> List[EvidenceItem]:
        values = list(items)
        for item in values:
            self.update_evidence_item(item)
        return values

    def update_evidence_item(self, item: EvidenceItem) -> EvidenceItem:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO evidence_items (
                    id, evaluation_run_id, project_id, raw_signal_id, cluster_id, dimension,
                    title, content, summary, url, source_platform, source_type, content_type,
                    author, published_at, fetched_at, engagement_metrics_json, hotness_score,
                    sentiment_label, sentiment_score, stance_label, credibility_score,
                    freshness_score, relevance_score, dedupe_hash, status, tags_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    evaluation_run_id = excluded.evaluation_run_id,
                    project_id = excluded.project_id,
                    raw_signal_id = excluded.raw_signal_id,
                    cluster_id = excluded.cluster_id,
                    dimension = excluded.dimension,
                    title = excluded.title,
                    content = excluded.content,
                    summary = excluded.summary,
                    url = excluded.url,
                    source_platform = excluded.source_platform,
                    source_type = excluded.source_type,
                    content_type = excluded.content_type,
                    author = excluded.author,
                    published_at = excluded.published_at,
                    fetched_at = excluded.fetched_at,
                    engagement_metrics_json = excluded.engagement_metrics_json,
                    hotness_score = excluded.hotness_score,
                    sentiment_label = excluded.sentiment_label,
                    sentiment_score = excluded.sentiment_score,
                    stance_label = excluded.stance_label,
                    credibility_score = excluded.credibility_score,
                    freshness_score = excluded.freshness_score,
                    relevance_score = excluded.relevance_score,
                    dedupe_hash = excluded.dedupe_hash,
                    status = excluded.status,
                    tags_json = excluded.tags_json
                """,
                (
                    item.id,
                    item.evaluation_run_id,
                    item.project_id,
                    item.raw_signal_id,
                    item.cluster_id,
                    item.dimension,
                    item.title,
                    item.content,
                    item.summary,
                    item.url,
                    item.source_platform,
                    item.source_type,
                    item.content_type,
                    item.author,
                    _dt(item.published_at),
                    _dt(item.fetched_at),
                    _json(item.engagement_metrics),
                    item.hotness_score,
                    item.sentiment_label,
                    item.sentiment_score,
                    item.stance_label,
                    item.credibility_score,
                    item.freshness_score,
                    item.relevance_score,
                    item.dedupe_hash,
                    item.status,
                    _json(item.tags),
                ),
            )
        return item

    def get_evidence_item(self, evidence_id: str) -> Optional[EvidenceItem]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM evidence_items WHERE id = ?", (evidence_id,)).fetchone()
        return self._evidence_item_from_row(row) if row else None

    def list_evidence(self, run_id: str) -> List[EvidenceItem]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM evidence_items
                WHERE evaluation_run_id = ?
                ORDER BY rowid
                """,
                (run_id,),
            ).fetchall()
        return [self._evidence_item_from_row(row) for row in rows]

    def _evidence_item_from_row(self, row: sqlite3.Row) -> EvidenceItem:
        return EvidenceItem.parse_obj(
            {
                **dict(row),
                "engagement_metrics": _json_value(row["engagement_metrics_json"], {}),
                "tags": _json_value(row["tags_json"], []),
            }
        )

    def add_clusters(self, clusters: Iterable[EvidenceCluster]) -> List[EvidenceCluster]:
        values = list(clusters)
        for item in values:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO evidence_clusters (
                        id, evaluation_run_id, dimension, label, summary,
                        representative_evidence_ids_json, evidence_count, source_diversity,
                        avg_hotness_score, avg_sentiment_score, time_range_start, time_range_end
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        evaluation_run_id = excluded.evaluation_run_id,
                        dimension = excluded.dimension,
                        label = excluded.label,
                        summary = excluded.summary,
                        representative_evidence_ids_json = excluded.representative_evidence_ids_json,
                        evidence_count = excluded.evidence_count,
                        source_diversity = excluded.source_diversity,
                        avg_hotness_score = excluded.avg_hotness_score,
                        avg_sentiment_score = excluded.avg_sentiment_score,
                        time_range_start = excluded.time_range_start,
                        time_range_end = excluded.time_range_end
                    """,
                    (
                        item.id,
                        item.evaluation_run_id,
                        item.dimension,
                        item.label,
                        item.summary,
                        _json(item.representative_evidence_ids),
                        item.evidence_count,
                        item.source_diversity,
                        item.avg_hotness_score,
                        item.avg_sentiment_score,
                        _dt(item.time_range_start),
                        _dt(item.time_range_end),
                    ),
                )
        return values

    def list_clusters(self, run_id: str) -> List[EvidenceCluster]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM evidence_clusters
                WHERE evaluation_run_id = ?
                ORDER BY rowid
                """,
                (run_id,),
            ).fetchall()
        return [self._cluster_from_row(row) for row in rows]

    def _cluster_from_row(self, row: sqlite3.Row) -> EvidenceCluster:
        return EvidenceCluster.parse_obj(
            {
                **dict(row),
                "representative_evidence_ids": _json_value(
                    row["representative_evidence_ids_json"], []
                ),
            }
        )

    def add_scores(self, scores: Iterable[ScoreLedger]) -> List[ScoreLedger]:
        values = list(scores)
        for item in values:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO score_ledgers (
                        id, evaluation_run_id, dimension, score, confidence, weight, rationale,
                        positive_evidence_ids_json, negative_evidence_ids_json,
                        missing_evidence_json, assumptions_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        evaluation_run_id = excluded.evaluation_run_id,
                        dimension = excluded.dimension,
                        score = excluded.score,
                        confidence = excluded.confidence,
                        weight = excluded.weight,
                        rationale = excluded.rationale,
                        positive_evidence_ids_json = excluded.positive_evidence_ids_json,
                        negative_evidence_ids_json = excluded.negative_evidence_ids_json,
                        missing_evidence_json = excluded.missing_evidence_json,
                        assumptions_json = excluded.assumptions_json,
                        created_at = excluded.created_at
                    """,
                    (
                        item.id,
                        item.evaluation_run_id,
                        item.dimension,
                        item.score,
                        item.confidence,
                        item.weight,
                        item.rationale,
                        _json(item.positive_evidence_ids),
                        _json(item.negative_evidence_ids),
                        _json(item.missing_evidence),
                        _json(item.assumptions),
                        _dt(item.created_at),
                    ),
                )
        return values

    def list_scores(self, run_id: str) -> List[ScoreLedger]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM score_ledgers
                WHERE evaluation_run_id = ?
                ORDER BY rowid
                """,
                (run_id,),
            ).fetchall()
        return [self._score_from_row(row) for row in rows]

    def _score_from_row(self, row: sqlite3.Row) -> ScoreLedger:
        return ScoreLedger.parse_obj(
            {
                **dict(row),
                "positive_evidence_ids": _json_value(row["positive_evidence_ids_json"], []),
                "negative_evidence_ids": _json_value(row["negative_evidence_ids_json"], []),
                "missing_evidence": _json_value(row["missing_evidence_json"], []),
                "assumptions": _json_value(row["assumptions_json"], []),
            }
        )

    def add_gate_decision(self, decision: GateDecision) -> GateDecision:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO gate_decisions (
                    id, evaluation_run_id, project_id, action, total_score, confidence,
                    reason, next_steps_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    evaluation_run_id = excluded.evaluation_run_id,
                    project_id = excluded.project_id,
                    action = excluded.action,
                    total_score = excluded.total_score,
                    confidence = excluded.confidence,
                    reason = excluded.reason,
                    next_steps_json = excluded.next_steps_json,
                    created_at = excluded.created_at
                """,
                (
                    decision.id,
                    decision.evaluation_run_id,
                    decision.project_id,
                    decision.action,
                    decision.total_score,
                    decision.confidence,
                    decision.reason,
                    _json(decision.next_steps),
                    _dt(decision.created_at),
                ),
            )
        return decision

    def get_latest_gate_decision(self, run_id: str) -> Optional[GateDecision]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM gate_decisions
                WHERE evaluation_run_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (run_id,),
            ).fetchone()
        return self._gate_decision_from_row(row) if row else None

    def _gate_decision_from_row(self, row: sqlite3.Row) -> GateDecision:
        return GateDecision.parse_obj(
            {
                **dict(row),
                "next_steps": _json_value(row["next_steps_json"], []),
            }
        )

    def add_report(self, report: EvaluationReport) -> EvaluationReport:
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT markdown FROM evaluation_reports WHERE id = ?",
                (report.id,),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO evaluation_reports (
                    id, evaluation_run_id, project_id, report_type, title, markdown_path,
                    markdown, structured_data_json, evidence_refs_json, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    evaluation_run_id = excluded.evaluation_run_id,
                    project_id = excluded.project_id,
                    report_type = excluded.report_type,
                    title = excluded.title,
                    markdown_path = excluded.markdown_path,
                    markdown = COALESCE(excluded.markdown, evaluation_reports.markdown),
                    structured_data_json = excluded.structured_data_json,
                    evidence_refs_json = excluded.evidence_refs_json,
                    status = excluded.status,
                    created_at = excluded.created_at
                """,
                (
                    report.id,
                    report.evaluation_run_id,
                    report.project_id,
                    report.report_type,
                    report.title,
                    report.markdown_path,
                    existing["markdown"] if existing else None,
                    _json(report.structured_data),
                    _json(report.evidence_refs),
                    report.status,
                    _dt(report.created_at),
                ),
            )
        return report

    def get_report(self, report_id: str) -> Optional[EvaluationReport]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM evaluation_reports WHERE id = ?", (report_id,)).fetchone()
        return self._report_from_row(row) if row else None

    def list_reports(self, run_id: str) -> List[EvaluationReport]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM evaluation_reports
                WHERE evaluation_run_id = ?
                ORDER BY rowid
                """,
                (run_id,),
            ).fetchall()
        return [self._report_from_row(row) for row in rows]

    def save_report_markdown(self, report_id: str, markdown: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE evaluation_reports SET markdown = ? WHERE id = ?",
                (markdown, report_id),
            )

    def get_report_markdown(self, report_id: str) -> Optional[str]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT markdown FROM evaluation_reports WHERE id = ?",
                (report_id,),
            ).fetchone()
        return str(row["markdown"]) if row and row["markdown"] is not None else None

    def _report_from_row(self, row: sqlite3.Row) -> EvaluationReport:
        return EvaluationReport.parse_obj(
            {
                **dict(row),
                "structured_data": _json_value(row["structured_data_json"], {}),
                "evidence_refs": _json_value(row["evidence_refs_json"], []),
            }
        )

    def add_llm_call_log(self, log: LLMCallLog, persist: bool = True) -> LLMCallLog:
        with self._lock:
            if persist:
                self._upsert_llm_call_log(log)
                self.live_llm_call_logs.pop(log.id, None)
            else:
                self.live_llm_call_logs[log.id] = log
            return log

    def update_llm_call_log(self, log: LLMCallLog, persist: bool = True) -> LLMCallLog:
        log.updated_at = utc_now()
        with self._lock:
            if persist:
                self._upsert_llm_call_log(log)
                self.live_llm_call_logs.pop(log.id, None)
            else:
                self.live_llm_call_logs[log.id] = log
            return log

    def _upsert_llm_call_log(self, log: LLMCallLog) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO llm_call_logs (
                    id, evaluation_run_id, provider, model, purpose, dimension, query,
                    status, request_payload_json, event_count, reasoning_text,
                    output_text, raw_events_json, error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    evaluation_run_id = excluded.evaluation_run_id,
                    provider = excluded.provider,
                    model = excluded.model,
                    purpose = excluded.purpose,
                    dimension = excluded.dimension,
                    query = excluded.query,
                    status = excluded.status,
                    request_payload_json = excluded.request_payload_json,
                    event_count = excluded.event_count,
                    reasoning_text = excluded.reasoning_text,
                    output_text = excluded.output_text,
                    raw_events_json = excluded.raw_events_json,
                    error = excluded.error,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                """,
                (
                    log.id,
                    log.evaluation_run_id,
                    log.provider,
                    log.model,
                    log.purpose,
                    log.dimension,
                    log.query,
                    log.status,
                    _json(log.request_payload),
                    log.event_count,
                    log.reasoning_text,
                    log.output_text,
                    _json(log.raw_events),
                    log.error,
                    _dt(log.created_at),
                    _dt(log.updated_at),
                ),
            )

    def list_llm_call_logs(self, run_id: str) -> List[LLMCallLog]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM llm_call_logs
                WHERE evaluation_run_id = ?
                ORDER BY rowid
                """,
                (run_id,),
            ).fetchall()
        logs_by_id = {item.id: item for item in (self._llm_call_log_from_row(row) for row in rows)}
        for item in self.live_llm_call_logs.values():
            if item.evaluation_run_id == run_id:
                logs_by_id[item.id] = item
        return sorted(logs_by_id.values(), key=lambda item: item.created_at)

    def _llm_call_log_from_row(self, row: sqlite3.Row) -> LLMCallLog:
        return LLMCallLog.parse_obj(
            {
                **dict(row),
                "request_payload": _json_value(row["request_payload_json"], {}),
                "raw_events": _json_value(row["raw_events_json"], []),
            }
        )

    def add_event(self, event: EventRecord) -> EventRecord:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO event_records (
                    id, evaluation_run_id, event_type, payload_json, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    evaluation_run_id = excluded.evaluation_run_id,
                    event_type = excluded.event_type,
                    payload_json = excluded.payload_json,
                    created_at = excluded.created_at
                """,
                (
                    event.id,
                    event.evaluation_run_id,
                    event.event_type,
                    _json(event.payload),
                    _dt(event.created_at),
                ),
            )
        return event

    def list_events(self, run_id: str) -> List[EventRecord]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM event_records
                WHERE evaluation_run_id = ?
                ORDER BY rowid
                """,
                (run_id,),
            ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def _event_from_row(self, row: sqlite3.Row) -> EventRecord:
        return EventRecord.parse_obj(
            {
                **dict(row),
                "payload": _json_value(row["payload_json"], {}),
            }
        )
