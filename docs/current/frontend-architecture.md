# Gem Cutter 正式版前端交互与代码架构设计

> Status: Active current design.
> Scope: React + Vite 正式前端的信息架构、交互和代码组织。

本文定义 Gem Cutter 从静态 MVP demo 升级到正式 React + Vite 工作台的第一版方案。目标不是先堆满所有功能，而是搭出可持续开发的专业前端骨架，让证据、评分、门禁、报告和 PRD 成为用户可理解、可复盘、可推进的工作流。

## 1. 产品交互定位

正式版前端应从“单页调试 demo”升级为“商业机会评估工作台”。

核心用户任务：

- 输入一个热点、产品想法或市场机会。
- 查看评估任务的阶段进度、证据覆盖和模型调用状态。
- 按维度审阅 Evidence Ledger 与 Score Ledger。
- 理解 GateDecision 为什么是 `go`、`conditional_go`、`hold` 或 `stop`。
- 在 gate 通过后生成并审阅 MVP PRD。
- 回看历史项目、报告和运行记录。

设计原则：

- 证据优先：页面主视觉不围绕 Markdown 报告，而围绕证据、评分和门禁。
- 阶段明确：用户始终知道系统处于计划、搜索、归一化、聚类、评分、门禁还是报告阶段。
- 可审计：每个关键分数、报告和 PRD 都能回到 run、evidence 和 score。
- 专业克制：使用清晰的信息密度、强状态表达、可扫描的表格/卡片，而不是聊天式自由输出。

## 2. 信息架构

首版正式前端采用 6 个主页面：

| Route | 页面 | 主要任务 |
| --- | --- | --- |
| `/dashboard` | 指挥台 | 查看系统状态、最近项目、评估漏斗和关键风险 |
| `/projects` | 机会项目 | 创建/浏览 OpportunityProject，进入详情 |
| `/projects/:projectId` | 项目工作台 | 审阅单个项目的运行、证据、评分、门禁和报告 |
| `/runs` | 运行中心 | 查看 EvaluationRun 状态、失败、阶段和模型调用 |
| `/reports` | 产物中心 | 查看评估报告与 PRD 入口 |
| `/settings` | 系统设置 | 查看 API、LLM、搜索 provider 和运行参数 |

后续扩展页面：

- `/evidence`：跨项目 Evidence Ledger 检索。
- `/templates`：评估模板、评分 rubric 和行业模板。
- `/operations`：运营实验、客户反馈、舆情回流。

## 3. 核心交互流

### 3.1 创建并评估机会

```text
Dashboard / Projects
-> Create Opportunity
-> POST /api/projects
-> POST /api/projects/{id}/evaluations
-> Project Workspace
-> SSE / polling 更新运行状态
-> Evidence + Score + Gate + Report
```

交互要求：

- 创建后立即进入项目工作台，而不是停留在表单页。
- 运行中顶部保持阶段状态和关键计数。
- 搜索阶段显示当前 dimension 和 research question。
- 失败时显示失败阶段、错误和下一步操作。

### 3.2 审阅项目结果

项目工作台采用“三栏证据工作流”：

- 左侧：项目上下文、run timeline、gate 状态。
- 中间：评分账本、证据覆盖、关键风险。
- 右侧：报告/PRD、模型日志、下一步动作。

核心行为：

- 点击评分维度，筛选对应证据。
- 点击证据，显示来源、可信度、热度、情感、URL。
- Gate 为 `go/conditional_go` 时，显示“生成 PRD”主行动。
- Gate 为 `hold/stop` 时，主行动变为“补充证据”或“归档复盘”。

### 3.3 设置与调试

设置页只暴露非敏感信息：

- API base URL。
- LLM provider。
- Search provider。
- Ark 是否配置。
- 模型名、stream、tool_choice、搜索并发参数。

不得展示 API key。

## 4. 视觉语言

建议视觉方向：`research command center`。

- 色彩：暖白底、深墨绿、琥珀状态色、红色风险色。
- 背景：低对比径向渐变和网格纹理，强调“分析台”而不是普通后台。
- 字体：标题使用 `Space Grotesk`，正文使用 `IBM Plex Sans` / `Noto Sans SC`。
- 动效：页面入场、卡片阶梯浮现、状态 pill 轻微过渡。避免无意义弹跳。
- 信息密度：卡片用于概览，表格/列表用于证据和日志，右侧 inspector 用于细节。

## 5. 代码架构

```text
frontend/
  index.html
  package.json
  vite.config.ts
  src/
    main.tsx
    app/
      App.tsx
      providers.tsx
    layouts/
      AppShell.tsx
    pages/
      dashboard/
      projects/
        detail/
      runs/
      reports/
      settings/
    components/
      workspace/
      charts/
      ui/
    services/
      api.ts
    constants/
      navigation.ts
    types/
      api.ts
    styles/
      index.css
```

分层职责：

- `app/`：应用入口、全局 provider、路由组装。
- `layouts/`：Shell、导航、页面容器，不包含业务请求细节。
- `pages/`：页面级编排，负责调用 query/mutation。
- `components/workspace/`：项目工作台专用组件，例如评分账本、证据板、阶段轨。
- `services/`：后端 API client、SSE client、错误归一化。
- `types/`：与后端 API 对齐的 TypeScript 类型。
- `styles/`：设计 token、全局 layout、组件基础样式。

## 6. API 集成边界

首版前端对接当前后端已有接口：

| 前端能力 | 后端接口 |
| --- | --- |
| 配置状态 | `GET /api/config/status` |
| 项目列表 | `GET /api/projects` |
| 项目详情 | `GET /api/projects/{project_id}` |
| 创建项目 | `POST /api/projects` |
| 启动评估 | `POST /api/projects/{project_id}/evaluations` |
| 运行详情 | `GET /api/evaluations/{run_id}` |
| 聚合视图 | `GET /api/evaluations/{run_id}/view` |
| 证据账本 | `GET /api/evaluations/{run_id}/evidence` |
| 评分账本 | `GET /api/evaluations/{run_id}/scores` |
| 模型日志 | `GET /api/evaluations/{run_id}/llm-logs` |
| 生成 PRD | `POST /api/evaluations/{run_id}/prd` |
| 报告 Markdown | `GET /api/reports/{report_id}/markdown` |
| 事件流 | `GET /api/evaluations/{run_id}/stream` |

后续建议补充的后端接口：

- `GET /api/evaluations`：运行列表。
- `GET /api/reports`：报告列表。
- `PATCH /api/evidence/{id}`：人工标记证据状态。
- `POST /api/evaluations/{id}/evidence/manual`：人工补充证据。
- `POST /api/evaluations/{id}/gate-decisions`：人工覆盖 gate。

## 7. 开发里程碑

### F0：正式前端骨架

- React + Vite + TypeScript。
- AppShell、路由、设计 token、API client。
- Dashboard、Projects、Project Detail、Runs、Reports、Settings 页面骨架。
- 旧静态 demo 归档到 `frontend/legacy/mvp-demo.html`。

### F1：工作台可用

- 创建项目并启动评估。
- 项目详情页展示 run、evidence、score、gate、report。
- 运行中自动轮询或 SSE 更新。
- PRD 生成按钮与状态反馈。

### F2：专业审阅体验

- 评分维度和证据联动筛选。
- 报告 Markdown viewer。
- 模型日志 inspector。
- 失败状态和补救动作。

### F3：人工复核能力

- 人工添加证据。
- 证据标记 valid/invalid/duplicate。
- 人工 gate override。
- 重新渲染报告。

