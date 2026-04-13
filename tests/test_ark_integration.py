import json
import unittest

import httpx

from backend.app.core.config import AppSettings
from backend.app.domain.sources import ArkBuiltinSearchAdapter, SourceSearchRequest
from backend.app.integrations.ark.client import ArkResponsesClient
from backend.app.integrations.ark.prompts import EVIDENCE_SEARCH_DEVELOPER_PROMPT
from backend.app.integrations.ark.schemas import ArkEvidenceSearchResult, evidence_search_json_schema


class ArkIntegrationTest(unittest.TestCase):
    def test_ark_client_builds_web_search_json_schema_request(self):
        captured = {}

        def handler(request):
            captured["body"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json={
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(
                                        {
                                            "items": [],
                                            "search_summary": "ok",
                                            "missing_evidence": [],
                                        }
                                    ),
                                }
                            ]
                        }
                    ]
                },
            )

        settings = AppSettings.parse_obj(
            {
                "search": {"provider": "ark_builtin"},
                "ark": {
                    "api_key": "test-key",
                    "model": "doubao-seed-1-8-251228",
                    "enable_tool_choice": True,
                },
            }
        )
        client = ArkResponsesClient(settings.ark, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        result = client.create_json(
            developer_prompt=EVIDENCE_SEARCH_DEVELOPER_PROMPT,
            user_prompt="topic=test",
            schema_name="evidence_search_result",
            schema=evidence_search_json_schema(),
            tools=[{"type": "web_search", "limit": 10, "max_keyword": 3}],
            use_tool_choice=True,
            response_model=ArkEvidenceSearchResult,
        )

        self.assertEqual(result["search_summary"], "ok")
        body = captured["body"]
        self.assertEqual(body["model"], "doubao-seed-1-8-251228")
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(body["tools"][0]["type"], "web_search")
        self.assertEqual(body["tool_choice"], "auto")
        self.assertEqual(body["text"]["format"]["type"], "json_schema")

    def test_ark_builtin_search_adapter_maps_response_to_raw_signal(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(
                                        {
                                            "items": [
                                                {
                                                    "title": "Evidence title",
                                                    "url": "https://example.com/evidence",
                                                    "source_platform": "web",
                                                    "source_type": "web",
                                                    "published_at": "2026-04-12T00:00:00",
                                                    "content": "Users ask for faster video script workflows.",
                                                    "summary": "Users want faster workflows.",
                                                    "supported_claims": ["user pain exists"],
                                                    "credibility_hint": 0.7,
                                                    "relevance_hint": 0.8,
                                                    "hotness_hint": 0.6,
                                                    "sentiment_hint": "negative",
                                                    "risk_flags": ["workflow_friction"],
                                                }
                                            ],
                                            "search_summary": "found one item",
                                            "missing_evidence": [],
                                        }
                                    ),
                                }
                            ]
                        }
                    ]
                },
            )

        settings = AppSettings.parse_obj(
            {
                "search": {"provider": "ark_builtin"},
                "ark": {
                    "api_key": "test-key",
                    "model": "doubao-seed-1-8-251228",
                    "enable_tool_choice": True,
                },
            }
        )
        client = ArkResponsesClient(settings.ark, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        adapter = ArkBuiltinSearchAdapter(settings=settings, client=client)
        signals = adapter.search(
            SourceSearchRequest(
                evaluation_run_id="run_test",
                dimension="user_pain",
                topic="AI video scripts",
                query="user pain evidence",
                target_market="China creators",
                limit=1,
            )
        )

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].source_adapter, "ark_builtin_web_search")
        self.assertEqual(signals[0].url, "https://example.com/evidence")
        self.assertEqual(signals[0].raw_payload["credibility_hint"], 0.7)
        self.assertEqual(signals[0].raw_payload["sentiment_hint"], "negative")


if __name__ == "__main__":
    unittest.main()
