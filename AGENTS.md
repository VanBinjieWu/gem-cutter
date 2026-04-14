# AGENTS.md

This file gives coding agents the project-specific context needed to work safely in `gem-cutter`.

## Project

Gem Cutter MVP is an evidence-first commercial evaluation agent project. The current vertical slice is:

```text
OpportunityProject
-> EvaluationRun
-> EvaluationPlan
-> RawSignal
-> EvidenceItem
-> EvidenceCluster
-> ScoreLedger
-> GateDecision
-> EvaluationReport / PRD Report
```

The important design rule: do not turn this into a free-form report generator. Reports and PRDs should be grounded in structured evidence and score ledgers. LLM PRD generation is allowed only after a `go` or `conditional_go` Gate and must pass Pydantic schema validation before Markdown is stored.

## Environment

Use the conda environment:

```powershell
conda activate gem-cutter
python main.py
```

Without activation:

```powershell
conda run -n gem-cutter python main.py
```

Dependency files:

```text
requirements.txt
environment.yml
```

Pinned runtime dependencies currently include:

```text
fastapi==0.125.0
uvicorn[standard]==0.44.0
pydantic==1.10.26
httpx==0.28.1
```

## Run And Test

Do not run tests automatically by default. Run tests only when the user asks for them, or when a change is risky enough that verification is clearly needed; in that case, state what you plan to run first.

Run tests:

```powershell
conda run -n gem-cutter python -m unittest discover -s tests -v
```

Check dependency consistency:

```powershell
conda run -n gem-cutter python -m pip check
```

Run backend:

```powershell
conda run -n gem-cutter python main.py
```

Default service URLs:

```text
API: http://127.0.0.1:8000
Docs: http://127.0.0.1:8000/docs
Config status: http://127.0.0.1:8000/api/config/status
```

The frontend is now an official React + Vite workspace:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` and point it at the backend API `http://127.0.0.1:8000`. The old static demo is archived at `frontend/legacy/mvp-demo.html`.

## Configuration

Runtime config is JSON-based:

```text
config/settings.json
config/settings.example.json
```

`config/settings.json` is ignored by git because it may contain secrets. Do not commit API keys.

Mock mode:

```json
{
  "llm": {"provider": "mock"},
  "search": {"provider": "mock"}
}
```

Ark Responses API mode:

```json
{
  "llm": {"provider": "ark"},
  "search": {
    "provider": "ark_builtin",
    "max_workers": 10,
    "per_dimension_workers": 2,
    "evidence_per_dimension": 5
  },
  "ark": {
    "api_key": "YOUR_API_KEY",
    "base_url": "https://ark.cn-beijing.volces.com/api/v3/responses",
    "model": "doubao-seed-1-8-251228",
    "timeout_seconds": 300,
    "stream": true,
    "enable_tool_choice": true,
    "max_output_tokens": 12000
  }
}
```

Environment variable overrides are also supported:

```powershell
$env:ARK_API_KEY="YOUR_API_KEY"
$env:GEM_CUTTER_LLM_PROVIDER="ark"
$env:GEM_CUTTER_SEARCH_PROVIDER="ark_builtin"
```

Never print, log, or persist the API key.

## Storage

The current local runtime uses SQLite, not Postgres:

```text
data/gem_cutter.db
```

Domain data is stored in dedicated SQLite tables rather than a JSON payload log. Report Markdown is persisted on the `evaluation_reports` table and exposed through `GET /api/reports/{report_id}/markdown`. `data/` is runtime output and is ignored by git. Do not rely on it for tests unless the test creates its own temporary store.

The intended future production path is Postgres plus optional pgvector, but do not migrate storage unless the task explicitly asks for it.

## Code Map

Main entrypoints:

```text
main.py
backend/app/main.py
```

Core domain:

```text
backend/app/domain/models.py
backend/app/domain/store.py
backend/app/domain/services.py
backend/app/domain/sources.py
```

Ark integration:

```text
backend/app/core/config.py
backend/app/integrations/ark/client.py
backend/app/integrations/ark/schemas.py
backend/app/integrations/ark/prompts.py
backend/app/integrations/ark/errors.py
```

Tests:

```text
tests/test_evaluation_pipeline.py
tests/test_ark_integration.py
```

Design docs:

```text
docs/11-mvp-enhanced-design.md
docs/12-ark-responses-llm-search-integration-plan.md
docs/09-mvp-business-evaluation-chain-design.md
docs/05-data-model.md
```

## Current LLM/Search State

Mock mode is the default. Ark integration code exists, but true Ark calls require:

1. API key in `config/settings.json` or `ARK_API_KEY`.
2. `search.provider = "ark_builtin"`.
3. Ark built-in `web_search` enabled for the account/project.

The model target is:

```text
doubao-seed-1-8-251228
```

The target endpoint is:

```text
POST https://ark.cn-beijing.volces.com/api/v3/responses
```

`tool_choice` is considered supported for this model in this project and is configurable through:

```json
"enable_tool_choice": true
```

Keep the switch; it is useful for debugging tool-call compatibility.

Ark calls stream by default. Model call logs are stored per evaluation run and exposed at:

```text
GET /api/evaluations/{run_id}/llm-logs
```

Use this endpoint and the static UI model log section to inspect streamed reasoning summaries and output text.

Evidence search runs dimensions concurrently. Keep `search.max_workers` bounded, and tune `search.per_dimension_workers` plus `search.evidence_per_dimension` together. The current local target is 2 search branches per dimension and 5 deduped evidence items per dimension.

## Development Rules

- Preserve the `RawSignal -> EvidenceItem -> EvidenceCluster -> ScoreLedger -> GateDecision` chain.
- Keep mock adapters and tests working even after adding real Ark calls.
- Use fake transports/mocks for tests that exercise Ark behavior; do not require a real API key in CI or local unit tests.
- Validate LLM outputs with Pydantic before writing them to the store.
- Let backend code recompute totals, confidence caps, and gate decisions. Do not trust LLM arithmetic as final.
- Avoid storing secrets in `data/`, reports, logs, frontend files, docs, or tests.
- Keep runtime artifacts out of source control: `data/`, `server.out.log`, `server.err.log`, `__pycache__/`.
- The project is not currently a git repository in this workspace. Do not assume git commands will work.

## Recommended Next Step

When the Ark API key is provided:

1. Put it in `config/settings.json` or `ARK_API_KEY`.
2. Switch search provider to `ark_builtin`.
3. Restart the backend.
4. Run one real evaluation from the static frontend or `/docs`.
5. Inspect `RawSignal`, `EvidenceItem`, and generated PRD quality before adding LLM scoring.
