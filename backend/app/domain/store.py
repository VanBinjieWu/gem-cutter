from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Dict, Iterable, List, Optional

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
