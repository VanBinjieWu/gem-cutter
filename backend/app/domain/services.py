from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from backend.app.core.config import AppSettings, load_settings
from backend.app.integrations.ark.client import ArkResponsesClient
from backend.app.integrations.ark.prompts import PRD_DEVELOPER_PROMPT, build_prd_user_prompt
from backend.app.integrations.ark.schemas import ArkPrdDraftResult, prd_draft_json_schema

from .models import (
    DIMENSION_WEIGHTS,
    Dimension,
    EvaluationReport,
    EvaluationRun,
    EventRecord,
    EvidenceCluster,
    EvidenceItem,
    EvidenceStatus,
    GateAction,
    GateDecision,
    LLMCallLog,
    OpportunityProject,
    ProjectStatus,
    RawSignal,
    ReportType,
    RunStage,
    RunStatus,
    ScoreLedger,
    utc_now,
)
from .sources import SourceAdapter, SourceSearchRequest, default_adapters
from .store import StoreProtocol


class ProjectService:
    def __init__(self, store: StoreProtocol):
        self.store = store

    def create_project(
        self,
        title: str,
        input_topic: str,
        target_market: Optional[str] = None,
        target_user_hint: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> OpportunityProject:
        project = OpportunityProject(
            title=title,
            input_topic=input_topic,
            target_market=target_market,
            target_user_hint=target_user_hint,
            constraints=constraints or {},
        )
        return self.store.add_project(project)


class RunEvents:
    def __init__(self, store: StoreProtocol):
        self.store = store

    def emit(self, evaluation_run_id: str, event_type: str, **payload: Any) -> EventRecord:
        return self.store.add_event(
            EventRecord(evaluation_run_id=evaluation_run_id, event_type=event_type, payload=payload)
        )


class EvidenceService:
    def __init__(self, store: StoreProtocol):
        self.store = store

    def normalize(self, project: OpportunityProject, run: EvaluationRun) -> List[EvidenceItem]:
        seen_hashes = {item.dedupe_hash for item in self.store.list_evidence(run.id)}
        items: List[EvidenceItem] = []
        for signal in self.store.list_raw_signals(run.id):
            if signal.normalization_status == "success":
                continue
            payload = signal.raw_payload
            title = str(payload.get("title") or signal.query)
            content = str(payload.get("content") or "")
            dedupe_hash = self._dedupe_hash(signal.url, title)
            status = EvidenceStatus.DUPLICATE if dedupe_hash in seen_hashes else EvidenceStatus.VALID
            seen_hashes.add(dedupe_hash)

            evidence = EvidenceItem(
                evaluation_run_id=run.id,
                project_id=project.id,
                raw_signal_id=signal.id,
                dimension=signal.dimension,
                title=title,
                content=content,
                summary=str(payload.get("summary") or self._summarize(content)),
                url=signal.url,
                source_platform=signal.source_platform,
                source_type=signal.source_type,
                author=payload.get("author"),
                published_at=self._parse_datetime(payload.get("published_at")),
                fetched_at=signal.fetched_at,
                engagement_metrics=payload.get("engagement") or {},
                hotness_score=self._hint_or_default(payload.get("hotness_hint"), self._hotness(payload.get("engagement") or {})),
                sentiment_label=str(payload.get("sentiment_hint") or self._sentiment_label(content)),
                sentiment_score=self._sentiment_score(str(payload.get("sentiment_hint") or content)),
                stance_label="neutral",
                credibility_score=self._hint_or_default(payload.get("credibility_hint"), self._credibility(signal.source_type)),
                freshness_score=self._freshness(payload.get("published_at")),
                relevance_score=self._hint_or_default(
                    payload.get("relevance_hint"),
                    0.75 if signal.dimension in title or signal.dimension in content else 0.62,
                ),
                dedupe_hash=dedupe_hash,
                status=status,
                tags=[signal.dimension, signal.source_type] + list(payload.get("risk_flags") or []),
            )
            items.append(evidence)
            signal.normalization_status = "success"
            self.store.update_raw_signal(signal)

        return self.store.add_evidence_items(items)

    def cluster(self, run: EvaluationRun) -> List[EvidenceCluster]:
        grouped: Dict[str, List[EvidenceItem]] = defaultdict(list)
        for item in self.store.list_evidence(run.id):
            if item.status == EvidenceStatus.VALID:
                grouped[item.dimension].append(item)

        clusters: List[EvidenceCluster] = []
        for dimension, items in grouped.items():
            if not items:
                continue
            published = [item.published_at for item in items if item.published_at]
            cluster = EvidenceCluster(
                evaluation_run_id=run.id,
                dimension=dimension,
                label=f"{dimension} evidence cluster",
                summary=f"{len(items)} valid evidence items for {dimension}.",
                representative_evidence_ids=[item.id for item in items[:3]],
                evidence_count=len(items),
                source_diversity=len({item.source_platform for item in items}),
                avg_hotness_score=round(sum(item.hotness_score for item in items) / len(items), 3),
                avg_sentiment_score=round(sum(item.sentiment_score for item in items) / len(items), 3),
                time_range_start=min(published) if published else None,
                time_range_end=max(published) if published else None,
            )
            clusters.append(cluster)

        saved = self.store.add_clusters(clusters)
        for cluster in saved:
            for evidence_id in cluster.representative_evidence_ids:
                item = self.store.get_evidence_item(evidence_id)
                if not item:
                    continue
                item.cluster_id = cluster.id
                self.store.update_evidence_item(item)
        return saved

    @staticmethod
    def _dedupe_hash(url: Optional[str], title: str) -> str:
        key = (url or title).strip().lower()
        return hashlib.sha1(key.encode("utf-8")).hexdigest()

    @staticmethod
    def _summarize(content: str) -> str:
        return content[:240]

    @staticmethod
    def _credibility(source_type: str) -> float:
        return {
            "official": 0.85,
            "news": 0.75,
            "report": 0.75,
            "web": 0.60,
            "community": 0.55,
            "manual": 0.50,
        }.get(source_type, 0.45)

    @staticmethod
    def _hotness(metrics: Dict[str, Any]) -> float:
        weighted = (
            float(metrics.get("mentions", 0)) * 1.0
            + float(metrics.get("shares", 0)) * 2.0
            + float(metrics.get("comments", 0)) * 1.5
            + float(metrics.get("likes", 0)) * 0.5
        )
        return round(min(math.log1p(weighted) / 6.0, 1.0), 3)

    @staticmethod
    def _freshness(value: Any) -> float:
        published = EvidenceService._parse_datetime(value)
        if not published:
            return 0.5
        days = max((utc_now() - published).days, 0)
        if days <= 3:
            return 1.0
        if days <= 14:
            return 0.8
        if days <= 45:
            return 0.6
        return 0.35

    @staticmethod
    def _sentiment_label(content: str) -> str:
        text = content.lower()
        if any(word in text for word in ["risk", "concern", "complain", "friction", "copyright"]):
            return "negative"
        if any(word in text for word in ["rising", "budget", "subscription", "timely"]):
            return "positive"
        return "neutral"

    @staticmethod
    def _sentiment_score(content: str) -> float:
        if content in {"positive", "neutral", "negative", "mixed", "unknown"}:
            return {"positive": 0.6, "neutral": 0.0, "negative": -0.45, "mixed": -0.1, "unknown": 0.0}[content]
        label = EvidenceService._sentiment_label(content)
        return {"positive": 0.6, "neutral": 0.0, "negative": -0.45}.get(label, 0.0)

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    @staticmethod
    def _hint_or_default(value: Any, default: float) -> float:
        if value is None:
            return default
        try:
            return round(max(0.0, min(float(value), 1.0)), 3)
        except (TypeError, ValueError):
            return default


class ScoringService:
    def __init__(self, store: StoreProtocol):
        self.store = store

    def score(self, run: EvaluationRun) -> List[ScoreLedger]:
        evidence_by_dimension: Dict[str, List[EvidenceItem]] = defaultdict(list)
        for item in self.store.list_evidence(run.id):
            if item.status == EvidenceStatus.VALID:
                evidence_by_dimension[item.dimension].append(item)

        scores = []
        for dimension, weight in DIMENSION_WEIGHTS.items():
            items = evidence_by_dimension.get(dimension, [])
            score, rationale = self._dimension_score(dimension, items)
            confidence = self._confidence(items)
            positives = [item.id for item in items[:3]]
            negatives = [item.id for item in items if item.sentiment_score < -0.1][:2]
            missing = [] if len(items) >= 2 else [f"Need at least 2 valid evidence items for {dimension}."]
            scores.append(
                ScoreLedger(
                    evaluation_run_id=run.id,
                    dimension=dimension,
                    score=score,
                    confidence=confidence,
                    weight=weight,
                    rationale=rationale,
                    positive_evidence_ids=positives,
                    negative_evidence_ids=negatives,
                    missing_evidence=missing,
                    assumptions=[] if items else ["No evidence found; conservative default applied."],
                )
            )
        return self.store.add_scores(scores)

    def decide_gate(self, project: OpportunityProject, run: EvaluationRun) -> GateDecision:
        scores = self.store.list_scores(run.id)
        total = round(sum(item.score * item.weight for item in scores), 2)
        confidence = round(sum(item.confidence * item.weight for item in scores), 3)
        risk_score = next(
            (item.score for item in scores if item.dimension == Dimension.PUBLIC_OPINION_RISK.value),
            50.0,
        )
        valid_evidence_count = sum(
            1 for item in self.store.list_evidence(run.id) if item.status == EvidenceStatus.VALID
        )

        if risk_score < 35 or valid_evidence_count < 3 or total < 50:
            action = GateAction.STOP
            reason = "Evidence quality, risk, or total score is below the MVP threshold."
        elif total >= 75 and confidence >= 0.68 and risk_score >= 55:
            action = GateAction.GO
            reason = "The opportunity has enough evidence, confidence, and risk control for PRD drafting."
        elif total >= 62 and confidence >= 0.55:
            action = GateAction.CONDITIONAL_GO
            reason = "The opportunity is promising, but remaining assumptions must be validated."
        else:
            action = GateAction.HOLD
            reason = "The opportunity needs more evidence before product work."

        next_steps = {
            GateAction.GO: ["Draft MVP PRD.", "Validate top user pain with 3 interviews."],
            GateAction.CONDITIONAL_GO: ["Draft PRD with assumptions.", "Run focused evidence collection."],
            GateAction.HOLD: ["Collect more evidence for weak dimensions.", "Re-run scoring."],
            GateAction.STOP: ["Archive this run.", "Record counter-evidence and risk notes."],
        }[action]

        return self.store.add_gate_decision(
            GateDecision(
                evaluation_run_id=run.id,
                project_id=project.id,
                action=action,
                total_score=total,
                confidence=confidence,
                reason=reason,
                next_steps=next_steps,
            )
        )

    @staticmethod
    def _dimension_score(dimension: str, items: List[EvidenceItem]) -> tuple[float, str]:
        if not items:
            return 35.0, f"No valid evidence for {dimension}; conservative score applied."
        avg_hotness = sum(item.hotness_score for item in items) / len(items)
        avg_credibility = sum(item.credibility_score for item in items) / len(items)
        avg_freshness = sum(item.freshness_score for item in items) / len(items)
        avg_sentiment = sum(item.sentiment_score for item in items) / len(items)
        base = 45 + avg_credibility * 20 + avg_hotness * 20 + avg_freshness * 10

        if dimension == Dimension.USER_PAIN.value:
            base += 8 if avg_sentiment < 0 else 2
        elif dimension == Dimension.MONETIZATION.value:
            base += 6
        elif dimension == Dimension.COMPETITION_GAP.value:
            base += 4 if len(items) < 5 else -3
        elif dimension == Dimension.PUBLIC_OPINION_RISK.value:
            base += -10 if avg_sentiment < -0.2 else 4
        elif dimension == Dimension.TIMING_WINDOW.value:
            base += avg_freshness * 8

        score = round(max(0, min(base, 100)), 2)
        return score, f"Computed from {len(items)} evidence items for {dimension}."

    @staticmethod
    def _confidence(items: List[EvidenceItem]) -> float:
        if not items:
            return 0.25
        coverage_factor = min(len(items) / 3.0, 1.0)
        diversity_factor = min(len({item.source_platform for item in items}) / 2.0, 1.0)
        credibility_factor = sum(item.credibility_score for item in items) / len(items)
        confidence = min(coverage_factor, diversity_factor, credibility_factor)
        if len(items) < 2:
            confidence = min(confidence, 0.45)
        if len({item.source_platform for item in items}) < 2:
            confidence = min(confidence, 0.60)
        return round(confidence, 3)


class ReportService:
    def __init__(
        self,
        store: StoreProtocol,
        artifact_dir: str | Path = "data/reports",
        settings: Optional[AppSettings] = None,
    ):
        self.store = store
        self.artifact_dir = Path(artifact_dir)
        self.settings = settings or load_settings()
        self.ark_client = ArkResponsesClient(self.settings.ark)

    def render_evaluation_report(
        self, project: OpportunityProject, run: EvaluationRun, decision: GateDecision
    ) -> EvaluationReport:
        evidence = self.store.list_evidence(run.id)
        scores = self.store.list_scores(run.id)
        lines = [
            f"# Evaluation Report: {project.title}",
            "",
            f"- Gate: `{decision.action}`",
            f"- Total score: `{decision.total_score}`",
            f"- Confidence: `{decision.confidence}`",
            f"- Reason: {decision.reason}",
            "",
            "## Score Ledger",
        ]
        for score in scores:
            refs = ", ".join(score.positive_evidence_ids[:3]) or "none"
            lines.append(
                f"- `{score.dimension}`: {score.score} / confidence {score.confidence}. "
                f"{score.rationale} Evidence: {refs}"
            )
        lines.extend(["", "## Evidence"])
        for item in evidence:
            lines.append(f"- [{item.id}] {item.title} ({item.source_platform}, {item.status}) {item.url or ''}")
        lines.extend(["", "## Next Steps"])
        for step in decision.next_steps:
            lines.append(f"- {step}")

        structured = {
            "project_id": project.id,
            "evaluation_run_id": run.id,
            "gate": decision.dict(),
            "scores": [item.dict() for item in scores],
            "evidence_count": len(evidence),
        }
        return self._save_report(project, run, ReportType.EVALUATION, "Evaluation Report", lines, structured)

    def render_prd(self, project: OpportunityProject, run: EvaluationRun) -> EvaluationReport:
        decision = self.store.get_latest_gate_decision(run.id)
        if not decision or decision.action not in {GateAction.GO, GateAction.CONDITIONAL_GO}:
            raise ValueError("PRD can only be generated for go or conditional_go decisions.")

        if self.settings.llm.provider == "ark" and self.settings.ark_configured:
            return self._render_prd_with_llm(project, run, decision)
        return self._render_prd_with_template(project, run, decision)

    def _render_prd_with_template(
        self, project: OpportunityProject, run: EvaluationRun, decision: GateDecision
    ) -> EvaluationReport:
        lines = [
            f"# MVP PRD: {project.title}",
            "",
            "## Background",
            f"Input topic: {project.input_topic}",
            "",
            "## Target Users",
            project.target_user_hint or "To be validated during discovery.",
            "",
            "## MVP Scope",
            "- Evidence-backed evaluation workspace",
            "- Score ledger review",
            "- Gate decision and report export",
            "",
            "## Acceptance Criteria",
            "- Users can review evidence behind every score.",
            "- Gate decision is visible and auditable.",
            "- Conditional assumptions are listed before build work.",
            "",
            "## Open Assumptions",
        ]
        if decision.action == GateAction.CONDITIONAL_GO:
            lines.append("- Remaining evidence gaps must be validated before full build.")
        else:
            lines.append("- Validate the highest-risk assumption with users before launch.")

        structured = {"project_id": project.id, "evaluation_run_id": run.id, "gate": decision.dict()}
        return self._save_report(project, run, ReportType.PRD, "MVP PRD", lines, structured)

    def _render_prd_with_llm(
        self, project: OpportunityProject, run: EvaluationRun, decision: GateDecision
    ) -> EvaluationReport:
        context = self._prd_context(project, run, decision)
        result = self.ark_client.create_json(
            developer_prompt=PRD_DEVELOPER_PROMPT,
            user_prompt=build_prd_user_prompt(context),
            schema_name="prd_draft_result",
            schema=prd_draft_json_schema(),
            response_model=ArkPrdDraftResult,
            trace_sink=self._build_prd_trace_sink(run),
        )
        draft = ArkPrdDraftResult.parse_obj(result)
        self._sanitize_prd_evidence_refs(run, draft)
        lines = self._render_llm_prd_markdown(project, run, decision, draft)
        structured = {
            "project_id": project.id,
            "evaluation_run_id": run.id,
            "gate": decision.dict(),
            "prd": draft.dict(),
            "generator": "ark_llm",
        }
        return self._save_report(project, run, ReportType.PRD, draft.title or "MVP PRD", lines, structured)

    def _sanitize_prd_evidence_refs(self, run: EvaluationRun, draft: ArkPrdDraftResult) -> None:
        valid_refs = {
            item.id
            for item in self.store.list_evidence(run.id)
            if item.status in {EvidenceStatus.VALID, EvidenceStatus.MANUALLY_ADDED}
        }
        draft.evidence_refs = [item for item in draft.evidence_refs if item in valid_refs]
        for feature in draft.mvp_scope:
            feature.evidence_refs = [item for item in feature.evidence_refs if item in valid_refs]

    def _prd_context(
        self, project: OpportunityProject, run: EvaluationRun, decision: GateDecision
    ) -> Dict[str, Any]:
        evidence = [item for item in self.store.list_evidence(run.id) if item.status == EvidenceStatus.VALID]
        evidence_by_dimension: Dict[str, List[EvidenceItem]] = defaultdict(list)
        for item in evidence:
            evidence_by_dimension[item.dimension].append(item)

        evidence_payload = []
        for dimension in DIMENSION_WEIGHTS:
            items = sorted(
                evidence_by_dimension.get(dimension, []),
                key=lambda item: (item.relevance_score, item.credibility_score, item.hotness_score),
                reverse=True,
            )[:5]
            for item in items:
                evidence_payload.append(
                    {
                        "id": item.id,
                        "dimension": item.dimension,
                        "title": item.title,
                        "summary": item.summary[:300],
                        "url": item.url,
                        "source_platform": item.source_platform,
                        "credibility_score": item.credibility_score,
                        "hotness_score": item.hotness_score,
                        "sentiment_label": item.sentiment_label,
                        "tags": item.tags[:6],
                    }
                )

        return {
            "project": {
                "id": project.id,
                "title": project.title,
                "input_topic": project.input_topic,
                "target_market": project.target_market,
                "target_user_hint": project.target_user_hint,
                "constraints": project.constraints,
            },
            "gate_decision": decision.dict(),
            "scores": [item.dict() for item in self.store.list_scores(run.id)],
            "evidence": evidence_payload,
            "clusters": [item.dict() for item in self.store.list_clusters(run.id)],
        }

    def _render_llm_prd_markdown(
        self,
        project: OpportunityProject,
        run: EvaluationRun,
        decision: GateDecision,
        draft: ArkPrdDraftResult,
    ) -> List[str]:
        lines = [
            f"# {draft.title}",
            "",
            f"- Project: `{project.id}`",
            f"- Run: `{run.id}`",
            f"- Gate: `{decision.action}`",
            f"- Total score: `{decision.total_score}`",
            f"- Confidence: `{decision.confidence}`",
            "",
            "## Executive Summary",
            draft.executive_summary,
            "",
            "## Target Users",
        ]
        lines.extend(f"- {item}" for item in draft.target_users)
        lines.extend(["", "## Problem Statement", draft.problem_statement, "", "## Value Proposition", draft.value_proposition])
        lines.extend(["", "## Goals"])
        lines.extend(f"- {item}" for item in draft.goals)
        lines.extend(["", "## Non Goals"])
        lines.extend(f"- {item}" for item in draft.non_goals)
        lines.extend(["", "## MVP Scope"])
        for feature in draft.mvp_scope:
            lines.extend(["", f"### {feature.title}", feature.rationale])
            if feature.user_stories:
                lines.append("")
                lines.append("User stories:")
                lines.extend(f"- {item}" for item in feature.user_stories)
            if feature.acceptance_criteria:
                lines.append("")
                lines.append("Acceptance criteria:")
                lines.extend(f"- {item}" for item in feature.acceptance_criteria)
            if feature.evidence_refs:
                lines.append("")
                lines.append(f"Evidence: {', '.join(feature.evidence_refs)}")
        lines.extend(["", "## User Journey"])
        lines.extend(f"- {item}" for item in draft.user_journey)
        lines.extend(["", "## Metrics"])
        lines.extend(f"- {item}" for item in draft.metrics)
        lines.extend(["", "## Launch Plan"])
        lines.extend(f"- {item}" for item in draft.launch_plan)
        lines.extend(["", "## Risks And Mitigations"])
        lines.extend(f"- {item}" for item in draft.risks_and_mitigations)
        lines.extend(["", "## Open Assumptions"])
        lines.extend(f"- {item}" for item in draft.open_assumptions)
        lines.extend(["", "## Evidence References"])
        lines.extend(f"- {item}" for item in draft.evidence_refs)
        return lines

    def _build_prd_trace_sink(self, run: EvaluationRun):
        holder: Dict[str, Any] = {"log": None}

        def sink(event: str, payload: Dict[str, Any]) -> None:
            log = holder["log"]
            if event == "started":
                log = LLMCallLog(
                    evaluation_run_id=run.id,
                    provider="ark",
                    model=self.settings.ark.model,
                    purpose="prd_generation",
                    status="running",
                    request_payload=payload.get("request") or {},
                )
                holder["log"] = self.store.add_llm_call_log(log, persist=False)
                return
            if not log:
                return
            if event == "stream_event":
                log.event_count += 1
                log.reasoning_text += str(payload.get("reasoning_delta") or "")
                log.output_text += str(payload.get("output_delta") or "")
                self.store.update_llm_call_log(log, persist=False)
                return
            if event == "completed":
                log.status = "completed"
                log.event_count = int(payload.get("event_count") or log.event_count)
                if payload.get("reasoning_text"):
                    log.reasoning_text = str(payload["reasoning_text"])
                if payload.get("output_text"):
                    log.output_text = str(payload["output_text"])
                self.store.update_llm_call_log(log, persist=True)
                return
            if event == "failed":
                log.status = "failed"
                log.error = str(payload.get("error") or "Ark PRD generation failed.")
                self.store.update_llm_call_log(log, persist=True)

        return sink

    def _save_report(
        self,
        project: OpportunityProject,
        run: EvaluationRun,
        report_type: ReportType,
        title: str,
        lines: Iterable[str],
        structured: Dict[str, Any],
    ) -> EvaluationReport:
        markdown = "\n".join(lines) + "\n"
        refs = [
            item.id
            for item in self.store.list_evidence(run.id)
            if item.status in {EvidenceStatus.VALID, EvidenceStatus.MANUALLY_ADDED}
        ]
        report = EvaluationReport(
            evaluation_run_id=run.id,
            project_id=project.id,
            report_type=report_type,
            title=title,
            markdown_path="",
            structured_data=structured,
            evidence_refs=refs,
        )
        report.markdown_path = f"sqlite://reports/{report.id}/markdown"
        saved = self.store.add_report(report)
        self.store.save_report_markdown(saved.id, markdown)
        project.latest_report_id = saved.id
        self.store.update_project(project)
        return saved


class EvaluationService:
    def __init__(
        self,
        store: StoreProtocol,
        adapters: Optional[List[SourceAdapter]] = None,
        artifact_dir: str | Path = "data/reports",
        max_search_workers: int = 3,
        per_dimension_workers: int = 2,
        evidence_per_dimension: int = 5,
        settings: Optional[AppSettings] = None,
    ):
        self.store = store
        self.settings = settings or load_settings()
        self.events = RunEvents(store)
        self.evidence = EvidenceService(store)
        self.scoring = ScoringService(store)
        self.reports = ReportService(store, artifact_dir=artifact_dir, settings=self.settings)
        self.adapters = adapters or default_adapters(settings=self.settings, store=store)
        self.max_search_workers = max(1, max_search_workers)
        self.per_dimension_workers = max(1, per_dimension_workers)
        self.evidence_per_dimension = max(1, evidence_per_dimension)

    def start_run(self, project_id: str) -> EvaluationRun:
        project = self._require_project(project_id)
        run = EvaluationRun(project_id=project.id, topic_id=project.topic_id)
        saved = self.store.add_run(run)
        project.status = ProjectStatus.EVALUATING
        project.latest_evaluation_run_id = saved.id
        self.store.update_project(project)
        self.events.emit(saved.id, "evaluation.started", project_id=project.id)
        return saved

    def run(self, run_id: str) -> EvaluationRun:
        run = self._require_run(run_id)
        project = self._require_project(run.project_id)
        try:
            self._update_run(run, RunStatus.RUNNING, RunStage.PLANNING, 5, "Planning evaluation.")
            run.plan = self._build_plan(project)
            query_budget = sum(len(dimension["questions"]) for dimension in run.plan["dimensions"])
            run.budget = {
                "target_evidence_per_dimension": self.evidence_per_dimension,
                "max_queries": query_budget,
                "max_runtime_seconds": 600,
            }
            self.store.update_run(run)
            self.events.emit(
                run.id,
                "plan.created",
                dimension_count=len(run.plan["dimensions"]),
                query_budget=query_budget,
                target_evidence_per_dimension=self.evidence_per_dimension,
            )

            self._update_run(run, RunStatus.RUNNING, RunStage.COLLECTING_SIGNALS, 20, "Collecting raw signals.")
            raw_signals = self._collect_raw_signals(project, run)
            self.events.emit(run.id, "raw_signal.added", count=len(raw_signals))

            self._update_run(run, RunStatus.RUNNING, RunStage.NORMALIZING_EVIDENCE, 40, "Normalizing evidence.")
            evidence = self.evidence.normalize(project, run)
            self.events.emit(run.id, "evidence.added", count=len(evidence))

            self._update_run(run, RunStatus.RUNNING, RunStage.CLUSTERING_EVIDENCE, 55, "Clustering evidence.")
            clusters = self.evidence.cluster(run)
            self.events.emit(run.id, "evidence.clustered", cluster_count=len(clusters))

            self._update_run(run, RunStatus.RUNNING, RunStage.SCORING, 70, "Scoring opportunity.")
            scores = self.scoring.score(run)
            for score in scores:
                self.events.emit(
                    run.id,
                    "score.updated",
                    dimension=score.dimension,
                    score=score.score,
                    confidence=score.confidence,
                )

            self._update_run(run, RunStatus.RUNNING, RunStage.GATE_REVIEW, 82, "Deciding gate.")
            decision = self.scoring.decide_gate(project, run)
            self.events.emit(
                run.id,
                "gate.decided",
                gate=decision.action,
                total_score=decision.total_score,
                confidence=decision.confidence,
            )

            self._update_run(run, RunStatus.RUNNING, RunStage.RENDERING, 92, "Rendering report.")
            report = self.reports.render_evaluation_report(project, run, decision)
            self.events.emit(run.id, "report.generated", report_id=report.id)

            self._update_run(run, RunStatus.COMPLETED, RunStage.COMPLETED, 100, "Evaluation completed.")
            project.status = ProjectStatus.COMPLETED
            self.store.update_project(project)
            self.events.emit(run.id, "evaluation.completed", run_id=run.id)
            return run
        except Exception as exc:
            run.error = str(exc)
            self._update_run(run, RunStatus.FAILED, RunStage.FAILED, run.progress, str(exc))
            project.status = ProjectStatus.FAILED
            self.store.update_project(project)
            self.events.emit(run.id, "evaluation.failed", stage=run.stage, error=str(exc))
            raise

    def generate_prd(self, run_id: str) -> EvaluationReport:
        run = self._require_run(run_id)
        project = self._require_project(run.project_id)
        report = self.reports.render_prd(project, run)
        self.events.emit(run.id, "prd.generated", prd_report_id=report.id)
        return report

    def evaluation_view(self, run_id: str) -> Dict[str, Any]:
        run = self._require_run(run_id)
        project = self._require_project(run.project_id)
        evidence = self.store.list_evidence(run.id)
        valid_evidence = [item for item in evidence if item.status == EvidenceStatus.VALID]
        scores = self.store.list_scores(run.id)
        reports = self.store.list_reports(run.id)
        gate = self.store.get_latest_gate_decision(run.id)
        return {
            "project": project.dict(),
            "run": run.dict(),
            "plan": run.plan,
            "evidence_summary": {
                "raw_signal_count": len(self.store.list_raw_signals(run.id)),
                "valid_evidence_count": len(valid_evidence),
                "cluster_count": len(self.store.list_clusters(run.id)),
                "source_diversity": len({item.source_platform for item in valid_evidence}),
                "avg_credibility": self._avg([item.credibility_score for item in valid_evidence]),
                "avg_hotness": self._avg([item.hotness_score for item in valid_evidence]),
            },
            "score_summary": {
                "total_score": gate.total_score if gate else None,
                "overall_confidence": gate.confidence if gate else None,
                "dimensions": [item.dict() for item in scores],
            },
            "gate_decision": gate.dict() if gate else None,
            "reports": [item.dict() for item in reports],
            "llm_log_count": len(self.store.list_llm_call_logs(run.id)),
        }

    def _collect_raw_signals(self, project: OpportunityProject, run: EvaluationRun) -> List[RawSignal]:
        work_items: List[tuple[int, Dict[str, Any], str]] = []
        for dimension_index, dimension in enumerate(run.plan["dimensions"]):
            for question_index, question in enumerate(dimension["questions"]):
                work_items.append((dimension_index * 100 + question_index, dimension, question))

        if not work_items:
            return []

        signals: List[RawSignal] = []
        worker_count = min(self.max_search_workers, len(work_items))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_work_item = {
                executor.submit(self._collect_dimension_raw_signals, project, run, dimension, question): (
                    index,
                    dimension,
                    question,
                )
                for index, dimension, question in work_items
            }
            results: List[tuple[int, List[RawSignal]]] = []
            for future in as_completed(future_to_work_item):
                index, dimension, question = future_to_work_item[future]
                try:
                    results.append((index, future.result()))
                except Exception as exc:
                    self.events.emit(
                        run.id,
                        "evidence.search_failed",
                        dimension=dimension.get("name"),
                        query=question,
                        error=str(exc),
                    )
            for _, result in sorted(results, key=lambda item: item[0]):
                signals.extend(result)
        return self.store.add_raw_signals(self._dedupe_and_cap_raw_signals(signals, run))

    def _collect_dimension_raw_signals(
        self,
        project: OpportunityProject,
        run: EvaluationRun,
        dimension: Dict[str, Any],
        question: str,
    ) -> List[RawSignal]:
        request = SourceSearchRequest(
            evaluation_run_id=run.id,
            dimension=dimension["name"],
            topic=project.input_topic,
            query=question,
            target_market=project.target_market,
            limit=max(int(dimension.get("per_query_evidence_limit") or 1), 1),
        )
        self.events.emit(run.id, "evidence.search_started", dimension=dimension["name"], query=question)
        signals: List[RawSignal] = []
        for adapter in self.adapters:
            signals.extend(adapter.search(request))
        return signals

    def _dedupe_and_cap_raw_signals(self, signals: List[RawSignal], run: EvaluationRun) -> List[RawSignal]:
        dimension_order = {
            dimension["name"]: index
            for index, dimension in enumerate(run.plan.get("dimensions", []))
        }
        counts: Dict[str, int] = defaultdict(int)
        seen: set[str] = set()
        deduped: List[RawSignal] = []
        for signal in sorted(signals, key=lambda item: dimension_order.get(item.dimension, 999)):
            key = self._raw_signal_dedupe_key(signal)
            if key in seen:
                signal.normalization_status = "duplicate"
                continue
            if counts[signal.dimension] >= self.evidence_per_dimension:
                continue
            seen.add(key)
            counts[signal.dimension] += 1
            deduped.append(signal)
        return deduped

    @staticmethod
    def _raw_signal_dedupe_key(signal: RawSignal) -> str:
        title = str(signal.raw_payload.get("title") or "")
        key = (signal.url or title or signal.query).strip().lower()
        return hashlib.sha1(key.encode("utf-8")).hexdigest()

    def _build_plan(self, project: OpportunityProject) -> Dict[str, Any]:
        dimensions = []
        for dimension in DIMENSION_WEIGHTS:
            per_query_limit = max(math.ceil(self.evidence_per_dimension / self.per_dimension_workers) + 1, 1)
            dimensions.append(
                {
                    "name": dimension,
                    "required_evidence_count": self.evidence_per_dimension,
                    "search_workers": self.per_dimension_workers,
                    "per_query_evidence_limit": per_query_limit,
                    "preferred_sources": ["web", "news"],
                    "freshness_days": 30,
                    "questions": self._dimension_questions(project, dimension),
                }
            )
        return {"topic": project.input_topic, "dimensions": dimensions}

    def _dimension_questions(self, project: OpportunityProject, dimension: str) -> List[str]:
        templates = [
            "{topic} {dimension} recent evidence",
            "{topic} {dimension} user discussion market signals",
            "{topic} {dimension} official report community evidence",
        ]
        return [
            template.format(topic=project.input_topic, dimension=dimension)
            for template in templates[: self.per_dimension_workers]
        ]

    def _update_run(
        self, run: EvaluationRun, status: RunStatus, stage: RunStage, progress: int, message: str
    ) -> None:
        run.status = status
        run.stage = stage
        run.progress = progress
        run.message = message
        if status == RunStatus.RUNNING and not run.started_at:
            run.started_at = utc_now()
        if status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
            run.finished_at = utc_now()
        self.store.update_run(run)

    def _require_project(self, project_id: str) -> OpportunityProject:
        project = self.store.get_project(project_id)
        if not project:
            raise KeyError(f"Project not found: {project_id}")
        return project

    def _require_run(self, run_id: str) -> EvaluationRun:
        run = self.store.get_run(run_id)
        if not run:
            raise KeyError(f"Evaluation run not found: {run_id}")
        return run

    @staticmethod
    def _avg(values: List[float]) -> float:
        return round(sum(values) / len(values), 3) if values else 0.0
