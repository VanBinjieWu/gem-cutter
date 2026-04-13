from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List, Protocol

from pydantic import BaseModel

from backend.app.core.config import AppSettings, load_settings
from backend.app.integrations.ark.client import ArkResponsesClient
from backend.app.integrations.ark.errors import ArkConfigError, ArkError
from backend.app.integrations.ark.prompts import (
    EVIDENCE_SEARCH_DEVELOPER_PROMPT,
    build_evidence_search_user_prompt,
)
from backend.app.integrations.ark.schemas import ArkEvidenceSearchResult, evidence_search_json_schema

from .models import LLMCallLog, RawSignal, utc_now


class SourceSearchRequest(BaseModel):
    evaluation_run_id: str
    dimension: str
    topic: str
    query: str
    target_market: str | None = None
    limit: int = 2


class SourceAdapter(Protocol):
    name: str

    def search(self, request: SourceSearchRequest) -> List[RawSignal]:
        ...


class MockWebSearchAdapter:
    name = "web_search"

    def search(self, request: SourceSearchRequest) -> List[RawSignal]:
        now = utc_now()
        return [
            RawSignal(
                evaluation_run_id=request.evaluation_run_id,
                source_adapter=self.name,
                source_platform="web",
                source_type="web",
                dimension=request.dimension,
                query=request.query,
                url=f"https://example.com/{request.dimension}/{idx}",
                fetched_at=now,
                raw_payload={
                    "title": f"{request.topic}: web signal for {request.dimension} #{idx}",
                    "content": self._content(request, idx),
                    "author": "Gem Cutter mock web",
                    "published_at": (now - timedelta(days=idx * 3)).isoformat(),
                    "engagement": {"mentions": 20 + idx * 7, "shares": 5 + idx},
                },
            )
            for idx in range(1, request.limit + 1)
        ]

    @staticmethod
    def _content(request: SourceSearchRequest, idx: int) -> str:
        fragments = {
            "trend_strength": "Recent searches and creator discussions show rising attention.",
            "user_pain": "Users complain about workflow friction and ask for faster alternatives.",
            "monetization": "Several products use subscription pricing and teams mention budget fit.",
            "competition_gap": "Existing competitors solve adjacent needs but leave room for niche workflows.",
            "execution_feasibility": "A narrow MVP can be implemented with search, templates, and review loops.",
            "public_opinion_risk": "Some posts mention copyright, privacy, and platform policy concerns.",
            "timing_window": "The topic is timely, but the window depends on sustained user demand.",
        }
        return f"{fragments.get(request.dimension, 'Relevant market signal.')} Query={request.query}. Item={idx}."


class MockNewsSearchAdapter:
    name = "news_search"

    def search(self, request: SourceSearchRequest) -> List[RawSignal]:
        now = utc_now()
        return [
            RawSignal(
                evaluation_run_id=request.evaluation_run_id,
                source_adapter=self.name,
                source_platform="news",
                source_type="news",
                dimension=request.dimension,
                query=request.query,
                url=f"https://news.example.com/{request.dimension}/{idx}",
                fetched_at=now,
                raw_payload={
                    "title": f"{request.topic}: news context for {request.dimension} #{idx}",
                    "content": self._content(request, idx),
                    "author": "Gem Cutter mock news",
                    "published_at": (now - timedelta(days=idx)).isoformat(),
                    "engagement": {"mentions": 45 + idx * 11, "shares": 9 + idx * 2},
                },
            )
            for idx in range(1, request.limit + 1)
        ]

    @staticmethod
    def _content(request: SourceSearchRequest, idx: int) -> str:
        return (
            f"News coverage frames {request.topic} around {request.dimension}. "
            "It gives a recent, cross-source signal rather than a final conclusion. "
            f"Market={request.target_market or 'unspecified'}. Item={idx}."
        )


class ManualEvidenceAdapter:
    name = "manual"

    def search(self, request: SourceSearchRequest) -> List[RawSignal]:
        return []


class ArkBuiltinSearchAdapter:
    name = "ark_builtin_web_search"
    max_raw_events = 50

    def __init__(self, settings: AppSettings, client: ArkResponsesClient | None = None, store=None):
        self.settings = settings
        self.client = client or ArkResponsesClient(settings.ark)
        self.store = store

    def search(self, request: SourceSearchRequest) -> List[RawSignal]:
        if not self.settings.ark_configured:
            raise ArkConfigError("Ark API key is not configured.")

        result = self.client.create_json(
            developer_prompt=EVIDENCE_SEARCH_DEVELOPER_PROMPT,
            user_prompt=build_evidence_search_user_prompt(request),
            schema_name="evidence_search_result",
            schema=evidence_search_json_schema(),
            tools=[self._web_search_tool()],
            use_tool_choice=self.settings.ark.enable_tool_choice,
            response_model=ArkEvidenceSearchResult,
            trace_sink=self._build_trace_sink(request),
        )
        parsed = ArkEvidenceSearchResult.parse_obj(result)
        now = utc_now()
        signals = []
        for item in parsed.items[: request.limit]:
            signals.append(
                RawSignal(
                    evaluation_run_id=request.evaluation_run_id,
                    source_adapter=self.name,
                    source_platform=item.source_platform or "web",
                    source_type=item.source_type or "web",
                    dimension=request.dimension,
                    query=request.query,
                    url=item.url,
                    fetched_at=now,
                    raw_payload={
                        "title": item.title,
                        "content": item.content,
                        "summary": item.summary,
                        "author": "ark_builtin_search",
                        "published_at": item.published_at,
                        "engagement": {
                            "mentions": round(item.hotness_hint * 100, 3),
                        },
                        "supported_claims": item.supported_claims,
                        "credibility_hint": item.credibility_hint,
                        "relevance_hint": item.relevance_hint,
                        "hotness_hint": item.hotness_hint,
                        "sentiment_hint": item.sentiment_hint,
                        "risk_flags": item.risk_flags,
                        "search_summary": parsed.search_summary,
                        "missing_evidence": parsed.missing_evidence,
                    },
                )
            )
        return signals

    def _web_search_tool(self) -> dict:
        tool = {
            "type": "web_search",
            "limit": self.settings.ark.web_search.limit,
            "max_keyword": self.settings.ark.web_search.max_keyword,
            "user_location": self.settings.ark.web_search.user_location,
        }
        return tool

    def _build_trace_sink(self, request: SourceSearchRequest):
        if not self.store:
            return None

        holder: Dict[str, Any] = {"log": None}

        def sink(event: str, payload: Dict[str, Any]) -> None:
            log = holder["log"]
            if event == "started":
                log = LLMCallLog(
                    evaluation_run_id=request.evaluation_run_id,
                    provider="ark",
                    model=self.settings.ark.model,
                    purpose="evidence_search",
                    dimension=request.dimension,
                    query=request.query,
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
                log.raw_events.append(
                    {
                        "event_type": payload.get("event_type"),
                        "output_delta": payload.get("output_delta") or "",
                        "reasoning_delta": payload.get("reasoning_delta") or "",
                        "payload": payload.get("payload") or {},
                    }
                )
                if len(log.raw_events) > self.max_raw_events:
                    log.raw_events = log.raw_events[-self.max_raw_events :]
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
                log.error = str(payload.get("error") or "Ark request failed.")
                self.store.update_llm_call_log(log, persist=True)

        return sink


def default_adapters(settings: AppSettings | None = None, store=None) -> List[SourceAdapter]:
    settings = settings or load_settings()
    if settings.search.provider == "ark_builtin" and settings.ark_configured:
        return [ArkBuiltinSearchAdapter(settings, store=store), ManualEvidenceAdapter()]
    if settings.search.provider == "ark_builtin" and not settings.ark_configured:
        # Keep local demos runnable before the API key is configured.
        return [MockWebSearchAdapter(), MockNewsSearchAdapter(), ManualEvidenceAdapter()]
    return [MockWebSearchAdapter(), MockNewsSearchAdapter(), ManualEvidenceAdapter()]
