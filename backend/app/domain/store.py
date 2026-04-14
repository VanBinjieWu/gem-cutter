from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Dict, Iterable, List, Optional, Type, TypeVar

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
    StoreData,
    utc_now,
)

ModelT = TypeVar("ModelT")


class JsonStore:
    def __init__(self, path: str | Path = "data/gem_cutter_store.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self.live_llm_call_logs: Dict[str, LLMCallLog] = {}
        self.data = self._load()

    def _load(self) -> StoreData:
        if not self.path.exists():
            return StoreData()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return StoreData.parse_obj(raw)

    def save(self) -> None:
        with self._lock:
            self.path.write_text(self.data.json(indent=2, ensure_ascii=False), encoding="utf-8")

    def add_project(self, project: OpportunityProject) -> OpportunityProject:
        with self._lock:
            self.data.projects[project.id] = project
            self.save()
            return project

    def get_project(self, project_id: str) -> Optional[OpportunityProject]:
        return self.data.projects.get(project_id)

    def list_projects(self) -> List[OpportunityProject]:
        return sorted(self.data.projects.values(), key=lambda item: item.created_at, reverse=True)

    def update_project(self, project: OpportunityProject) -> OpportunityProject:
        project.updated_at = utc_now()
        with self._lock:
            self.data.projects[project.id] = project
            self.save()
            return project

    def add_run(self, run: EvaluationRun) -> EvaluationRun:
        with self._lock:
            self.data.runs[run.id] = run
            self.save()
            return run

    def get_run(self, run_id: str) -> Optional[EvaluationRun]:
        return self.data.runs.get(run_id)

    def update_run(self, run: EvaluationRun) -> EvaluationRun:
        with self._lock:
            self.data.runs[run.id] = run
            self.save()
            return run

    def add_raw_signals(self, signals: Iterable[RawSignal]) -> List[RawSignal]:
        items = list(signals)
        with self._lock:
            for item in items:
                self.data.raw_signals[item.id] = item
            self.save()
            return items

    def list_raw_signals(self, run_id: str) -> List[RawSignal]:
        return [item for item in self.data.raw_signals.values() if item.evaluation_run_id == run_id]

    def update_raw_signal(self, signal: RawSignal) -> RawSignal:
        with self._lock:
            self.data.raw_signals[signal.id] = signal
            self.save()
            return signal

    def add_evidence_items(self, items: Iterable[EvidenceItem]) -> List[EvidenceItem]:
        values = list(items)
        with self._lock:
            for item in values:
                self.data.evidence_items[item.id] = item
            self.save()
            return values

    def update_evidence_item(self, item: EvidenceItem) -> EvidenceItem:
        with self._lock:
            self.data.evidence_items[item.id] = item
            self.save()
            return item

    def get_evidence_item(self, evidence_id: str) -> Optional[EvidenceItem]:
        return self.data.evidence_items.get(evidence_id)

    def list_evidence(self, run_id: str) -> List[EvidenceItem]:
        return [item for item in self.data.evidence_items.values() if item.evaluation_run_id == run_id]

    def add_clusters(self, clusters: Iterable[EvidenceCluster]) -> List[EvidenceCluster]:
        values = list(clusters)
        with self._lock:
            for item in values:
                self.data.evidence_clusters[item.id] = item
            self.save()
            return values

    def list_clusters(self, run_id: str) -> List[EvidenceCluster]:
        return [item for item in self.data.evidence_clusters.values() if item.evaluation_run_id == run_id]

    def add_scores(self, scores: Iterable[ScoreLedger]) -> List[ScoreLedger]:
        values = list(scores)
        with self._lock:
            for item in values:
                self.data.score_ledgers[item.id] = item
            self.save()
            return values

    def list_scores(self, run_id: str) -> List[ScoreLedger]:
        return [item for item in self.data.score_ledgers.values() if item.evaluation_run_id == run_id]

    def add_gate_decision(self, decision: GateDecision) -> GateDecision:
        with self._lock:
            self.data.gate_decisions[decision.id] = decision
            self.save()
            return decision

    def get_latest_gate_decision(self, run_id: str) -> Optional[GateDecision]:
        decisions = [
            item for item in self.data.gate_decisions.values() if item.evaluation_run_id == run_id
        ]
        if not decisions:
            return None
        return sorted(decisions, key=lambda item: item.created_at, reverse=True)[0]

    def add_report(self, report: EvaluationReport) -> EvaluationReport:
        with self._lock:
            self.data.reports[report.id] = report
            self.save()
            return report

    def get_report(self, report_id: str) -> Optional[EvaluationReport]:
        return self.data.reports.get(report_id)

    def list_reports(self, run_id: str) -> List[EvaluationReport]:
        return [item for item in self.data.reports.values() if item.evaluation_run_id == run_id]

    def save_report_markdown(self, report_id: str, markdown: str) -> None:
        with self._lock:
            self.data.report_markdowns[report_id] = markdown
            self.save()

    def get_report_markdown(self, report_id: str) -> Optional[str]:
        return self.data.report_markdowns.get(report_id)

    def add_llm_call_log(self, log: LLMCallLog, persist: bool = True) -> LLMCallLog:
        with self._lock:
            if persist:
                self.data.llm_call_logs[log.id] = log
                self.live_llm_call_logs.pop(log.id, None)
                self.save()
            else:
                self.live_llm_call_logs[log.id] = log
            return log

    def update_llm_call_log(self, log: LLMCallLog, persist: bool = True) -> LLMCallLog:
        log.updated_at = utc_now()
        with self._lock:
            if persist:
                self.data.llm_call_logs[log.id] = log
                self.live_llm_call_logs.pop(log.id, None)
                self.save()
            else:
                self.live_llm_call_logs[log.id] = log
            return log

    def list_llm_call_logs(self, run_id: str) -> List[LLMCallLog]:
        logs_by_id = {
            item.id: item
            for item in self.data.llm_call_logs.values()
            if item.evaluation_run_id == run_id
        }
        for item in self.live_llm_call_logs.values():
            if item.evaluation_run_id == run_id:
                logs_by_id[item.id] = item
        logs = list(logs_by_id.values())
        return sorted(logs, key=lambda item: item.created_at)

    def add_event(self, event: EventRecord) -> EventRecord:
        with self._lock:
            self.data.events[event.id] = event
            self.save()
            return event

    def list_events(self, run_id: str) -> List[EventRecord]:
        events = [item for item in self.data.events.values() if item.evaluation_run_id == run_id]
        return sorted(events, key=lambda item: item.created_at)


class SQLiteStore:
    def __init__(self, path: str | Path = "data/gem_cutter.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self.live_llm_call_logs: Dict[str, LLMCallLog] = {}
        self._init_schema()

    def has_data(self) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT 1 FROM domain_entities LIMIT 1").fetchone()
        return bool(row)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS domain_entities (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    id TEXT NOT NULL,
                    evaluation_run_id TEXT,
                    project_id TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    payload TEXT NOT NULL,
                    UNIQUE(kind, id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_domain_entities_kind_run "
                "ON domain_entities(kind, evaluation_run_id, sequence)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_domain_entities_kind_project "
                "ON domain_entities(kind, project_id, sequence)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_domain_entities_kind_created "
                "ON domain_entities(kind, created_at)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS report_markdowns (
                    report_id TEXT PRIMARY KEY,
                    markdown TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _upsert(
        self,
        kind: str,
        item,
        evaluation_run_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        payload = item.json(ensure_ascii=False)
        created_at = getattr(item, "created_at", None)
        updated_at = getattr(item, "updated_at", None)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO domain_entities (
                    kind, id, evaluation_run_id, project_id, created_at, updated_at, payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(kind, id) DO UPDATE SET
                    evaluation_run_id = excluded.evaluation_run_id,
                    project_id = excluded.project_id,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    payload = excluded.payload
                """,
                (
                    kind,
                    item.id,
                    evaluation_run_id,
                    project_id,
                    created_at.isoformat() if created_at else None,
                    updated_at.isoformat() if updated_at else None,
                    payload,
                ),
            )
        return item

    def _get(self, kind: str, item_id: str, model: Type[ModelT]) -> Optional[ModelT]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM domain_entities WHERE kind = ? AND id = ?",
                (kind, item_id),
            ).fetchone()
        if not row:
            return None
        return model.parse_raw(row["payload"])

    def _list_by_run(self, kind: str, run_id: str, model: Type[ModelT]) -> List[ModelT]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload FROM domain_entities
                WHERE kind = ? AND evaluation_run_id = ?
                ORDER BY sequence
                """,
                (kind, run_id),
            ).fetchall()
        return [model.parse_raw(row["payload"]) for row in rows]

    def add_project(self, project: OpportunityProject) -> OpportunityProject:
        return self._upsert("project", project, project_id=project.id)

    def get_project(self, project_id: str) -> Optional[OpportunityProject]:
        return self._get("project", project_id, OpportunityProject)

    def list_projects(self) -> List[OpportunityProject]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload FROM domain_entities
                WHERE kind = 'project'
                ORDER BY created_at DESC, sequence DESC
                """
            ).fetchall()
        return [OpportunityProject.parse_raw(row["payload"]) for row in rows]

    def update_project(self, project: OpportunityProject) -> OpportunityProject:
        project.updated_at = utc_now()
        return self._upsert("project", project, project_id=project.id)

    def add_run(self, run: EvaluationRun) -> EvaluationRun:
        return self._upsert("run", run, evaluation_run_id=run.id, project_id=run.project_id)

    def get_run(self, run_id: str) -> Optional[EvaluationRun]:
        return self._get("run", run_id, EvaluationRun)

    def update_run(self, run: EvaluationRun) -> EvaluationRun:
        return self._upsert("run", run, evaluation_run_id=run.id, project_id=run.project_id)

    def add_raw_signals(self, signals: Iterable[RawSignal]) -> List[RawSignal]:
        items = list(signals)
        for item in items:
            self._upsert("raw_signal", item, evaluation_run_id=item.evaluation_run_id)
        return items

    def list_raw_signals(self, run_id: str) -> List[RawSignal]:
        return self._list_by_run("raw_signal", run_id, RawSignal)

    def update_raw_signal(self, signal: RawSignal) -> RawSignal:
        return self._upsert("raw_signal", signal, evaluation_run_id=signal.evaluation_run_id)

    def add_evidence_items(self, items: Iterable[EvidenceItem]) -> List[EvidenceItem]:
        values = list(items)
        for item in values:
            self._upsert(
                "evidence_item",
                item,
                evaluation_run_id=item.evaluation_run_id,
                project_id=item.project_id,
            )
        return values

    def update_evidence_item(self, item: EvidenceItem) -> EvidenceItem:
        return self._upsert(
            "evidence_item",
            item,
            evaluation_run_id=item.evaluation_run_id,
            project_id=item.project_id,
        )

    def get_evidence_item(self, evidence_id: str) -> Optional[EvidenceItem]:
        return self._get("evidence_item", evidence_id, EvidenceItem)

    def list_evidence(self, run_id: str) -> List[EvidenceItem]:
        return self._list_by_run("evidence_item", run_id, EvidenceItem)

    def add_clusters(self, clusters: Iterable[EvidenceCluster]) -> List[EvidenceCluster]:
        values = list(clusters)
        for item in values:
            self._upsert("evidence_cluster", item, evaluation_run_id=item.evaluation_run_id)
        return values

    def list_clusters(self, run_id: str) -> List[EvidenceCluster]:
        return self._list_by_run("evidence_cluster", run_id, EvidenceCluster)

    def add_scores(self, scores: Iterable[ScoreLedger]) -> List[ScoreLedger]:
        values = list(scores)
        for item in values:
            self._upsert("score_ledger", item, evaluation_run_id=item.evaluation_run_id)
        return values

    def list_scores(self, run_id: str) -> List[ScoreLedger]:
        return self._list_by_run("score_ledger", run_id, ScoreLedger)

    def add_gate_decision(self, decision: GateDecision) -> GateDecision:
        return self._upsert(
            "gate_decision",
            decision,
            evaluation_run_id=decision.evaluation_run_id,
            project_id=decision.project_id,
        )

    def get_latest_gate_decision(self, run_id: str) -> Optional[GateDecision]:
        decisions = self._list_by_run("gate_decision", run_id, GateDecision)
        if not decisions:
            return None
        return sorted(decisions, key=lambda item: item.created_at, reverse=True)[0]

    def add_report(self, report: EvaluationReport) -> EvaluationReport:
        return self._upsert(
            "report",
            report,
            evaluation_run_id=report.evaluation_run_id,
            project_id=report.project_id,
        )

    def get_report(self, report_id: str) -> Optional[EvaluationReport]:
        return self._get("report", report_id, EvaluationReport)

    def list_reports(self, run_id: str) -> List[EvaluationReport]:
        return self._list_by_run("report", run_id, EvaluationReport)

    def save_report_markdown(self, report_id: str, markdown: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO report_markdowns (report_id, markdown, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(report_id) DO UPDATE SET
                    markdown = excluded.markdown,
                    updated_at = excluded.updated_at
                """,
                (report_id, markdown, utc_now().isoformat()),
            )

    def get_report_markdown(self, report_id: str) -> Optional[str]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT markdown FROM report_markdowns WHERE report_id = ?",
                (report_id,),
            ).fetchone()
        if not row:
            return None
        return str(row["markdown"])

    def add_llm_call_log(self, log: LLMCallLog, persist: bool = True) -> LLMCallLog:
        with self._lock:
            if persist:
                self._upsert("llm_call_log", log, evaluation_run_id=log.evaluation_run_id)
                self.live_llm_call_logs.pop(log.id, None)
            else:
                self.live_llm_call_logs[log.id] = log
            return log

    def update_llm_call_log(self, log: LLMCallLog, persist: bool = True) -> LLMCallLog:
        log.updated_at = utc_now()
        with self._lock:
            if persist:
                self._upsert("llm_call_log", log, evaluation_run_id=log.evaluation_run_id)
                self.live_llm_call_logs.pop(log.id, None)
            else:
                self.live_llm_call_logs[log.id] = log
            return log

    def list_llm_call_logs(self, run_id: str) -> List[LLMCallLog]:
        logs_by_id = {
            item.id: item for item in self._list_by_run("llm_call_log", run_id, LLMCallLog)
        }
        for item in self.live_llm_call_logs.values():
            if item.evaluation_run_id == run_id:
                logs_by_id[item.id] = item
        logs = list(logs_by_id.values())
        return sorted(logs, key=lambda item: item.created_at)

    def add_event(self, event: EventRecord) -> EventRecord:
        return self._upsert("event", event, evaluation_run_id=event.evaluation_run_id)

    def list_events(self, run_id: str) -> List[EventRecord]:
        return self._list_by_run("event", run_id, EventRecord)


def migrate_json_store_to_sqlite(json_path: str | Path, sqlite_store: SQLiteStore) -> None:
    path = Path(json_path)
    if not path.exists():
        return

    data = StoreData.parse_obj(json.loads(path.read_text(encoding="utf-8")))

    for item in data.projects.values():
        sqlite_store.add_project(item)
    for item in data.runs.values():
        sqlite_store.add_run(item)
    sqlite_store.add_raw_signals(data.raw_signals.values())
    sqlite_store.add_evidence_items(data.evidence_items.values())
    sqlite_store.add_clusters(data.evidence_clusters.values())
    sqlite_store.add_scores(data.score_ledgers.values())
    for item in data.gate_decisions.values():
        sqlite_store.add_gate_decision(item)
    for item in data.reports.values():
        sqlite_store.add_report(item)
        markdown = data.report_markdowns.get(item.id)
        if markdown is None and item.markdown_path and not item.markdown_path.startswith("sqlite://"):
            markdown_path = Path(item.markdown_path)
            if markdown_path.exists():
                markdown = markdown_path.read_text(encoding="utf-8")
        if markdown is not None:
            sqlite_store.save_report_markdown(item.id, markdown)
    for item in data.llm_call_logs.values():
        sqlite_store.add_llm_call_log(item)
    for item in data.events.values():
        sqlite_store.add_event(item)
