from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import httpx
from pydantic import BaseModel, ValidationError

from backend.app.core.config import ArkSettings

from .errors import (
    ArkAuthenticationError,
    ArkConfigError,
    ArkRateLimitError,
    ArkResponseError,
    ArkResponseParseError,
    ArkToolUnavailableError,
)


TraceSink = Callable[[str, Dict[str, Any]], None]


class ArkResponsesClient:
    def __init__(self, settings: ArkSettings, http_client: Optional[httpx.Client] = None):
        self.settings = settings
        self.http_client = http_client or httpx.Client(timeout=settings.timeout_seconds)

    def create_json(
        self,
        developer_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]] = None,
        use_tool_choice: bool = False,
        response_model: Optional[type[BaseModel]] = None,
        trace_sink: Optional[TraceSink] = None,
    ) -> Dict[str, Any]:
        body = self._build_body(
            developer_prompt=developer_prompt,
            user_prompt=user_prompt,
            tools=tools,
            schema_name=schema_name,
            schema=schema,
            use_tool_choice=use_tool_choice,
        )
        if trace_sink:
            trace_sink("started", {"request": redact_request_body(body)})
        try:
            if self.settings.stream:
                data = self._post_stream_with_retry(body, trace_sink)
            else:
                response = self._post_with_retry(body)
                data = response.json()
                if trace_sink:
                    trace_sink("completed", {"response": compact_payload(data), "output_text": extract_response_text(data)})
            text = extract_response_text(data)
            parsed = parse_json_text(text)
            if response_model:
                try:
                    return response_model.parse_obj(parsed).dict()
                except ValidationError as exc:
                    raise ArkResponseParseError(str(exc)) from exc
            return parsed
        except Exception as exc:
            if trace_sink:
                trace_sink("failed", {"error": str(exc)})
            raise

    def _build_body(
        self,
        developer_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: Dict[str, Any],
        tools: Optional[List[Dict[str, Any]]] = None,
        use_tool_choice: bool = False,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "model": self.settings.model,
            "input": [
                {
                    "role": "developer",
                    "type": "message",
                    "content": developer_prompt,
                },
                {
                    "role": "user",
                    "type": "message",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
            "thinking": self.settings.thinking.dict(),
            "reasoning": self.settings.reasoning.dict(),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": False,
                }
            },
            "store": False,
            "stream": self.settings.stream,
            "temperature": self.settings.temperature,
            "max_output_tokens": self.settings.max_output_tokens,
        }
        if tools:
            body["tools"] = tools
            body["max_tool_calls"] = 3
            if use_tool_choice and self.settings.enable_tool_choice:
                body["tool_choice"] = "auto"
        return body

    def _post_with_retry(self, body: Dict[str, Any]) -> httpx.Response:
        if not self.settings.api_key.strip():
            raise ArkConfigError("ARK API key is not configured.")

        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        attempts = max(self.settings.max_retries, 0) + 1
        last_error: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                response = self.http_client.post(self.settings.base_url, headers=headers, json=body)
                if response.status_code in {401, 403}:
                    raise ArkAuthenticationError(response.text)
                if response.status_code == 429:
                    raise ArkRateLimitError(response.text)
                if response.status_code >= 500:
                    raise ArkResponseError(response.text)
                if response.status_code >= 400:
                    if "tool" in response.text.lower() or "web_search" in response.text:
                        raise ArkToolUnavailableError(response.text)
                    raise ArkResponseError(response.text)
                return response
            except (ArkRateLimitError, ArkResponseError) as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    break
                time.sleep(0.5 * (2**attempt))
        if last_error:
            raise last_error
        raise ArkResponseError("Ark request failed without a response.")

    def _post_stream_with_retry(
        self, body: Dict[str, Any], trace_sink: Optional[TraceSink] = None
    ) -> Dict[str, Any]:
        if not self.settings.api_key.strip():
            raise ArkConfigError("ARK API key is not configured.")

        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        attempts = max(self.settings.max_retries, 0) + 1
        last_error: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                with self.http_client.stream("POST", self.settings.base_url, headers=headers, json=body) as response:
                    if response.status_code in {401, 403}:
                        raise ArkAuthenticationError(response.read().decode("utf-8", errors="replace"))
                    if response.status_code == 429:
                        raise ArkRateLimitError(response.read().decode("utf-8", errors="replace"))
                    if response.status_code >= 500:
                        raise ArkResponseError(response.read().decode("utf-8", errors="replace"))
                    if response.status_code >= 400:
                        error_text = response.read().decode("utf-8", errors="replace")
                        if "tool" in error_text.lower() or "web_search" in error_text:
                            raise ArkToolUnavailableError(error_text)
                        raise ArkResponseError(error_text)

                    content_type = response.headers.get("content-type", "")
                    if "text/event-stream" not in content_type.lower():
                        raw = response.read().decode("utf-8", errors="replace")
                        data = json.loads(raw)
                        if trace_sink:
                            trace_sink(
                                "completed",
                                {"response": compact_payload(data), "output_text": extract_response_text(data)},
                            )
                        return data

                    output_text, reasoning_text, event_count = read_stream_response(response, trace_sink)
                    data = {"output_text": output_text}
                    if trace_sink:
                        trace_sink(
                            "completed",
                            {
                                "response": {"output_text": output_text},
                                "output_text": output_text,
                                "reasoning_text": reasoning_text,
                                "event_count": event_count,
                            },
                        )
                    return data
            except (ArkRateLimitError, ArkResponseError, httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    break
                time.sleep(0.5 * (2**attempt))
        if last_error:
            raise last_error
        raise ArkResponseError("Ark stream request failed without a response.")


def extract_response_text(response: Dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    chunks: List[str] = []
    for output_item in response.get("output", []) or []:
        content = output_item.get("content", []) if isinstance(output_item, dict) else []
        for content_item in content:
            if not isinstance(content_item, dict):
                continue
            if isinstance(content_item.get("text"), str):
                chunks.append(content_item["text"])
            elif isinstance(content_item.get("content"), str):
                chunks.append(content_item["content"])
    if chunks:
        return "\n".join(chunks)

    if isinstance(response.get("text"), str):
        return response["text"]
    raise ArkResponseParseError("No response text found in Ark response.")


def read_stream_response(
    response: httpx.Response, trace_sink: Optional[TraceSink] = None
) -> Tuple[str, str, int]:
    output_parts: List[str] = []
    reasoning_parts: List[str] = []
    final_output_text = ""
    event_count = 0
    for event_type, payload in iter_sse_json_events(response):
        event_count += 1
        text_delta = extract_stream_delta(event_type, payload, "output")
        reasoning_delta = extract_stream_delta(event_type, payload, "reasoning")
        if text_delta:
            output_parts.append(text_delta)
        if reasoning_delta:
            reasoning_parts.append(reasoning_delta)

        kind = str(payload.get("type") or event_type)
        if kind == "response.completed" and isinstance(payload.get("response"), dict):
            try:
                final_output_text = extract_response_text(payload["response"])
            except ArkResponseParseError:
                final_output_text = final_output_text

        if trace_sink:
            trace_sink(
                "stream_event",
                {
                    "event_type": kind,
                    "output_delta": text_delta,
                    "reasoning_delta": reasoning_delta,
                    "payload": compact_payload(payload),
                },
            )
    return final_output_text or "".join(output_parts), "".join(reasoning_parts), event_count


def iter_sse_json_events(response: httpx.Response) -> Iterable[Tuple[str, Dict[str, Any]]]:
    event_type = "message"
    data_lines: List[str] = []
    for line in response.iter_lines():
        if line == "":
            if data_lines:
                data = "\n".join(data_lines).strip()
                data_lines = []
                if data == "[DONE]":
                    break
                try:
                    yield event_type, json.loads(data)
                except json.JSONDecodeError:
                    yield event_type, {"type": "unparsed_sse_event", "data": data}
            event_type = "message"
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_type = line[6:].strip() or "message"
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    if data_lines:
        data = "\n".join(data_lines).strip()
        if data != "[DONE]":
            try:
                yield event_type, json.loads(data)
            except json.JSONDecodeError:
                yield event_type, {"type": "unparsed_sse_event", "data": data}


def extract_stream_delta(event_type: str, payload: Dict[str, Any], target: str) -> str:
    kind = str(payload.get("type") or event_type).lower()
    if "delta" not in kind:
        return ""
    if target == "reasoning":
        if not any(token in kind for token in ["reasoning", "thinking"]):
            return ""
    else:
        if any(token in kind for token in ["reasoning", "thinking"]):
            return ""
        if not any(token in kind for token in ["output_text", "message", "text"]):
            return ""

    for key in ["delta", "text", "content"]:
        value = payload.get(key)
        if isinstance(value, str):
            return value
    value = payload.get("summary")
    if isinstance(value, list):
        return "".join(item.get("text", "") for item in value if isinstance(item, dict))
    return ""


def redact_request_body(body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "model": body.get("model"),
        "stream": body.get("stream"),
        "thinking": body.get("thinking"),
        "reasoning": body.get("reasoning"),
        "text": body.get("text"),
        "tools": body.get("tools"),
        "tool_choice": body.get("tool_choice"),
        "max_tool_calls": body.get("max_tool_calls"),
        "temperature": body.get("temperature"),
        "max_output_tokens": body.get("max_output_tokens"),
    }


def compact_payload(payload: Any, limit: int = 4000) -> Any:
    text = json.dumps(payload, ensure_ascii=False, default=str)
    if len(text) <= limit:
        return payload
    return {"truncated": True, "preview": text[:limit]}


def parse_json_text(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ArkResponseParseError("No JSON object found in Ark response text.")
    try:
        return json.loads(stripped[start : end + 1])
    except json.JSONDecodeError as exc:
        decoder = json.JSONDecoder()
        try:
            parsed, _ = decoder.raw_decode(stripped[start:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        raise ArkResponseParseError(str(exc)) from exc
