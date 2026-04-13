from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel, Field


DEFAULT_CONFIG_PATH = Path("config/settings.json")
EXAMPLE_CONFIG_PATH = Path("config/settings.example.json")


class ProviderSettings(BaseModel):
    provider: str = "mock"


class SearchSettings(ProviderSettings):
    max_workers: int = 3
    per_dimension_workers: int = 2
    evidence_per_dimension: int = 5


class ArkWebSearchSettings(BaseModel):
    limit: int = 10
    max_keyword: int = 3
    user_location: Dict[str, Any] = Field(
        default_factory=lambda: {"type": "approximate", "country": "中国"}
    )


class ArkThinkingSettings(BaseModel):
    type: str = "enabled"


class ArkReasoningSettings(BaseModel):
    effort: str = "low"


class ArkSettings(BaseModel):
    api_key: str = ""
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3/responses"
    model: str = "doubao-seed-1-8-251228"
    timeout_seconds: int = 300
    max_retries: int = 2
    enable_tool_choice: bool = True
    stream: bool = True
    web_search: ArkWebSearchSettings = Field(default_factory=ArkWebSearchSettings)
    thinking: ArkThinkingSettings = Field(default_factory=ArkThinkingSettings)
    reasoning: ArkReasoningSettings = Field(default_factory=ArkReasoningSettings)
    temperature: float = 0.2
    max_output_tokens: int = 12000


class AppSettings(BaseModel):
    llm: ProviderSettings = Field(default_factory=ProviderSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    ark: ArkSettings = Field(default_factory=ArkSettings)

    @property
    def ark_configured(self) -> bool:
        return bool(self.ark.api_key.strip())


def load_settings(path: str | Path | None = None) -> AppSettings:
    config_path = Path(path or os.getenv("GEM_CUTTER_CONFIG", DEFAULT_CONFIG_PATH))
    if config_path.exists():
        raw = _read_json(config_path)
    elif EXAMPLE_CONFIG_PATH.exists():
        raw = _read_json(EXAMPLE_CONFIG_PATH)
    else:
        raw = {}

    settings = AppSettings.parse_obj(raw)
    _apply_env_overrides(settings)
    return settings


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _apply_env_overrides(settings: AppSettings) -> None:
    if os.getenv("ARK_API_KEY"):
        settings.ark.api_key = os.environ["ARK_API_KEY"]
    if os.getenv("ARK_BASE_URL"):
        settings.ark.base_url = os.environ["ARK_BASE_URL"]
    if os.getenv("ARK_MODEL"):
        settings.ark.model = os.environ["ARK_MODEL"]
    if os.getenv("GEM_CUTTER_LLM_PROVIDER"):
        settings.llm.provider = os.environ["GEM_CUTTER_LLM_PROVIDER"]
    if os.getenv("GEM_CUTTER_SEARCH_PROVIDER"):
        settings.search.provider = os.environ["GEM_CUTTER_SEARCH_PROVIDER"]


def public_settings(settings: AppSettings) -> Dict[str, Any]:
    return {
        "llm_provider": settings.llm.provider,
        "search_provider": settings.search.provider,
        "search": settings.search.dict(),
        "ark": {
            "configured": settings.ark_configured,
            "base_url": settings.ark.base_url,
            "model": settings.ark.model,
            "timeout_seconds": settings.ark.timeout_seconds,
            "stream": settings.ark.stream,
            "enable_tool_choice": settings.ark.enable_tool_choice,
            "web_search": settings.ark.web_search.dict(),
        },
    }
