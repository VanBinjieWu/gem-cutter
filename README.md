# Gem Cutter

Gem Cutter 是一个“证据优先”的商业机会评估工作台，用于把一个热点、产品想法或市场机会，转换成可审计的评估链路、评分账本、Gate 决策和 PRD 草案。当前实现面向本地开发环境：后端使用 FastAPI，前端使用 React + Vite，存储使用 SQLite 关系表。

Gem Cutter is an evidence-first commercial opportunity evaluation workspace. It turns an idea, trend, or market opportunity into an auditable evaluation chain, score ledger, Gate decision, and PRD draft. The current implementation targets local development with FastAPI, React + Vite, and SQLite relational storage.

## 目录 / Contents

- [项目定位 / Product Positioning](#项目定位--product-positioning)
- [当前功能 / Current Capabilities](#当前功能--current-capabilities)
- [业务链路 / Business Chain](#业务链路--business-chain)
- [架构概览 / Architecture](#架构概览--architecture)
- [本地启动 / Local Setup](#本地启动--local-setup)
- [配置 / Configuration](#配置--configuration)
- [存储 / Storage](#存储--storage)
- [测试 / Tests](#测试--tests)
- [代码地图 / Code Map](#代码地图--code-map)
- [开发原则 / Development Principles](#开发原则--development-principles)

## 项目定位 / Product Positioning

Gem Cutter 不是自由格式报告生成器。它的核心约束是：报告、PRD 和后续产品判断必须来自结构化证据与评分账本，而不是让 LLM 直接给出不可追溯的结论。

Gem Cutter is not a free-form report generator. Its central constraint is that reports, PRDs, and product decisions must be grounded in structured evidence and score ledgers, rather than opaque LLM conclusions.

当前版本主要解决三件事：

- 把输入机会拆解成 7 个商业评估维度，并生成可执行的搜索计划。
- 将搜索结果标准化为证据项、证据簇和评分账本。
- 在 Gate 通过后生成报告或 PRD，并保留证据引用和模型调用日志。

The current version focuses on three jobs:

- Break an input opportunity into 7 commercial evaluation dimensions and an executable search plan.
- Normalize search results into evidence items, evidence clusters, and score ledgers.
- Generate reports or PRDs after the Gate allows it, while preserving evidence references and model call logs.

## 当前功能 / Current Capabilities

- OpportunityProject 创建与历史项目查看。
- EvaluationRun 状态机：planning、collecting signals、normalizing evidence、clustering、scoring、gate review、rendering、completed/failed。
- Mock source adapters，用于无 API key 的本地开发和单元测试。
- Ark Responses API 集成，可使用内置 `web_search` 进行真实联网搜索。
- `RawSignal -> EvidenceItem -> EvidenceCluster -> ScoreLedger -> GateDecision` 主链路。
- Markdown 评估报告生成，Markdown 正文持久化在 SQLite 的 `evaluation_reports` 表。
- Gate 为 `go` 或 `conditional_go` 时允许生成 PRD；Ark 模式下 PRD 输出必须通过 Pydantic schema 校验。
- FastAPI REST API、OpenAPI docs 和 SSE 事件流。
- React + Vite 正式前端工作台，覆盖项目、运行、报告、设置等核心入口。
- LLM 调用日志持久化，并通过 `/api/evaluations/{run_id}/llm-logs` 暴露。

Current capabilities:

- OpportunityProject creation and historical project views.
- EvaluationRun state machine covering planning, signal collection, evidence normalization, clustering, scoring, Gate review, rendering, and completion/failure.
- Mock source adapters for local development and tests without an API key.
- Ark Responses API integration with built-in `web_search` for real web search.
- The main `RawSignal -> EvidenceItem -> EvidenceCluster -> ScoreLedger -> GateDecision` chain.
- Markdown evaluation report generation, with Markdown persisted in the SQLite `evaluation_reports` table.
- PRD generation only after a `go` or `conditional_go` Gate; Ark PRD output must pass Pydantic schema validation.
- FastAPI REST API, OpenAPI docs, and SSE event stream.
- Official React + Vite frontend workspace for projects, runs, reports, and settings.
- Persistent LLM call logs exposed through `/api/evaluations/{run_id}/llm-logs`.

## 业务链路 / Business Chain

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

评估维度使用加权评分：

- `trend_strength`
- `user_pain`
- `monetization`
- `competition_gap`
- `execution_feasibility`
- `public_opinion_risk`
- `timing_window`

The evaluation dimensions are weighted and scored:

- `trend_strength`
- `user_pain`
- `monetization`
- `competition_gap`
- `execution_feasibility`
- `public_opinion_risk`
- `timing_window`

## 架构概览 / Architecture

```text
React + Vite Frontend
  -> FastAPI Backend
    -> Domain Services
      -> Source Adapters / Ark Responses API
      -> SQLite Relational Store
```

后端负责业务链路、证据标准化、评分复算、Gate 决策、报告保存和 PRD schema 校验。前端负责以工作台形式展示项目、运行状态、报告入口和配置状态。

The backend owns the business chain, evidence normalization, score recomputation, Gate decisions, report persistence, and PRD schema validation. The frontend presents projects, run status, report entry points, and configuration state in a workspace UI.

当前本地架构有意保持轻量：

- API：FastAPI + Pydantic。
- Frontend：React + Vite + TypeScript。
- Storage：SQLite 关系表。
- LLM/Search：Mock provider 或 Ark Responses API。
- Future production path：Postgres + optional pgvector, Redis/queue, object storage。

The local architecture is intentionally lightweight:

- API: FastAPI + Pydantic.
- Frontend: React + Vite + TypeScript.
- Storage: SQLite relational tables.
- LLM/Search: mock providers or Ark Responses API.
- Future production path: Postgres + optional pgvector, Redis/queue, and object storage.

## 本地启动 / Local Setup

### 1. Conda 环境 / Conda Environment

使用已有的 `gem-cutter` 环境：

Use the existing `gem-cutter` environment:

```powershell
conda activate gem-cutter
python -m pip install -r requirements.txt
```

如需重建或同步环境：

To recreate or update the environment:

```powershell
conda env update -n gem-cutter -f environment.yml
```

不激活环境时也可以运行：

Without activating the environment:

```powershell
conda run -n gem-cutter python main.py
```

### 2. 启动后端 / Run Backend

```powershell
conda activate gem-cutter
python main.py
```

默认地址：

Default URLs:

```text
API: http://127.0.0.1:8000
Docs: http://127.0.0.1:8000/docs
Config status: http://127.0.0.1:8000/api/config/status
Health: http://127.0.0.1:8000/health
```

### 3. 启动前端 / Run Frontend

在第二个终端中：

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

打开：

Open:

```text
http://127.0.0.1:5173
```

前端默认连接：

The frontend defaults to:

```text
http://127.0.0.1:8000
```

也可以在前端 Settings 页面调整 API base URL。旧静态 demo 已归档到：

You can change the API base URL from the frontend Settings page. The old static demo is archived at:

```text
frontend/legacy/mvp-demo.html
```

## 配置 / Configuration

运行配置来自：

Runtime configuration is loaded from:

```text
config/settings.json
config/settings.example.json
```

`config/settings.json` 被 git 忽略，因为它可能包含 API key。不要提交、打印或记录 API key。

`config/settings.json` is ignored by git because it may contain API keys. Do not commit, print, or log API keys.

### Mock Mode

```json
{
  "llm": {"provider": "mock"},
  "search": {"provider": "mock"}
}
```

### Ark Responses API Mode

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

环境变量也可以覆盖配置：

Environment variables can override local config:

```powershell
$env:ARK_API_KEY="YOUR_API_KEY"
$env:GEM_CUTTER_LLM_PROVIDER="ark"
$env:GEM_CUTTER_SEARCH_PROVIDER="ark_builtin"
```

Ark 搜索并发参数：

Ark search concurrency settings:

```json
"search": {
  "provider": "ark_builtin",
  "max_workers": 10,
  "per_dimension_workers": 2,
  "evidence_per_dimension": 5
}
```

## 存储 / Storage

当前本地运行使用 SQLite：

The current local runtime uses SQLite:

```text
data/gem_cutter.db
```

领域数据存储在专用关系表中，而不是通用 JSON payload 日志表。当前主要表：

Domain data is stored in dedicated relational tables rather than a generic JSON payload log. Main tables:

```text
opportunity_projects
evaluation_runs
raw_signals
evidence_items
evidence_clusters
score_ledgers
gate_decisions
evaluation_reports
llm_call_logs
event_records
```

嵌套字段仍然以 JSON 列保存，例如 `tags`、`raw_payload`、`structured_data`、`evidence_refs` 和 `raw_events`。报告 Markdown 正文保存在 `evaluation_reports.markdown`，并通过 API 暴露：

Nested fields still use JSON columns where appropriate, such as `tags`, `raw_payload`, `structured_data`, `evidence_refs`, and `raw_events`. Report Markdown is stored in `evaluation_reports.markdown` and exposed through:

```text
GET /api/reports/{report_id}/markdown
```

本轮 SQLite 关系表重构不迁移旧 JSON 数据。旧 `data/gem_cutter_store.json` 不再读取；旧通用表 `domain_entities` / `report_markdowns` 不再作为运行数据来源。

The current SQLite relational refactor does not migrate old JSON data. Old `data/gem_cutter_store.json` is no longer read; old generic tables such as `domain_entities` / `report_markdowns` are no longer used as runtime sources.

## 测试 / Tests

运行单元测试：

Run unit tests:

```powershell
conda run -n gem-cutter python -m unittest discover -s tests -v
```

检查依赖一致性：

Check dependency consistency:

```powershell
conda run -n gem-cutter python -m pip check
```

测试使用 mock 或 fake transport，不需要真实 Ark API key。

Tests use mock providers or fake transports and do not require a real Ark API key.

## 代码地图 / Code Map

入口：

Entrypoints:

```text
main.py
backend/app/main.py
```

核心领域：

Core domain:

```text
backend/app/domain/models.py
backend/app/domain/store.py
backend/app/domain/services.py
backend/app/domain/sources.py
```

Ark 集成：

Ark integration:

```text
backend/app/core/config.py
backend/app/integrations/ark/client.py
backend/app/integrations/ark/schemas.py
backend/app/integrations/ark/prompts.py
backend/app/integrations/ark/errors.py
```

前端：

Frontend:

```text
frontend/
frontend/src/app/
frontend/src/layouts/
frontend/src/pages/
frontend/src/components/
frontend/src/services/
frontend/src/types/
frontend/src/styles/
```

测试：

Tests:

```text
tests/test_evaluation_pipeline.py
tests/test_ark_integration.py
```

关键设计文档：

Key design docs:

```text
docs/current/domain-model.md
docs/current/evaluation-chain.md
docs/current/ark-integration.md
docs/current/frontend-architecture.md
```

## 开发原则 / Development Principles

- 保持证据链：不要绕过 `RawSignal -> EvidenceItem -> EvidenceCluster -> ScoreLedger -> GateDecision`。
- 后端复算总分、置信度和 Gate，不信任 LLM 算术作为最终结果。
- PRD 只能在 `go` 或 `conditional_go` Gate 后生成。
- LLM 输出在写入报告前必须通过 Pydantic schema 校验。
- Mock adapters 和测试必须继续可用，不依赖真实 API key。
- 不要提交 secrets、`config/settings.json`、`data/`、日志或运行产物。
- 本地 SQLite 是当前开发存储；Postgres + pgvector 是后续生产化目标。

Development principles:

- Preserve the evidence chain; do not bypass `RawSignal -> EvidenceItem -> EvidenceCluster -> ScoreLedger -> GateDecision`.
- Let the backend recompute totals, confidence caps, and Gate decisions; do not trust LLM arithmetic as final.
- Generate PRDs only after a `go` or `conditional_go` Gate.
- Validate LLM outputs with Pydantic before writing reports.
- Keep mock adapters and tests working without a real API key.
- Do not commit secrets, `config/settings.json`, `data/`, logs, or runtime artifacts.
- SQLite is the current local development store; Postgres + pgvector is the future production path.
