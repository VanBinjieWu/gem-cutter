# Gem Cutter 文档目录

本文档是 `docs/` 的导航入口。Gem Cutter 的文档按“当前事实源、产品规划、治理、研究参考、历史归档”重新分类，避免把早期推演材料和当前实现状态混在一起。

## 分类原则

| 分类 | 用途 | 维护策略 |
| --- | --- | --- |
| `current/` | 当前实现和近期开发应优先遵循的设计事实源 | 代码变更后优先同步 |
| `product/` | 产品需求、功能范围和路线图 | 产品方向变化时同步 |
| `governance/` | 风险、合规、安全、质量门禁 | 上线或接入外部能力前复查 |
| `research/` | 外部项目对标和架构研究 | 作为参考，不直接等同于实现承诺 |
| `archive/` | 早期 MVP 推演和历史设计 | 保留上下文，默认不作为当前实现依据 |

## 当前事实源

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| [current/system-overview.md](current/system-overview.md) | Active | 总体架构、模块边界、技术栈和运行流程 |
| [current/domain-model.md](current/domain-model.md) | Active | 领域实体、SQLite 关系表、报告与证据数据结构 |
| [current/evaluation-chain.md](current/evaluation-chain.md) | Active | `RawSignal -> EvidenceItem -> EvidenceCluster -> ScoreLedger -> GateDecision` 主链路 |
| [current/agent-workflows.md](current/agent-workflows.md) | Reference | Agent 角色、阶段状态机、评分机制和 Skill 设计 |
| [current/ark-integration.md](current/ark-integration.md) | Active | Ark Responses API、内置搜索、LLM PRD 生成接入方案 |
| [current/frontend-architecture.md](current/frontend-architecture.md) | Active | React + Vite 正式前端的信息架构、交互和代码组织 |

## 产品规划

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| [product/product-requirements.md](product/product-requirements.md) | Reference | 完整产品需求、角色、范围、流程和验收标准 |
| [product/feature-modules.md](product/feature-modules.md) | Reference | 功能模块拆分和长期能力图谱 |
| [product/roadmap.md](product/roadmap.md) | Reference | 从 MVP 到商业化版本的迭代路线 |

## 治理与风险

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| [governance/risk-and-compliance.md](governance/risk-and-compliance.md) | Reference | 风险、合规、安全、质量门禁和人工复核策略 |

## 研究参考

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| [research/bettafish-mirofish-reference.md](research/bettafish-mirofish-reference.md) | Research | BettaFish/MiroFish 对标分析和可迁移设计启发 |

## 历史归档

| 文档 | 状态 | 说明 |
| --- | --- | --- |
| [archive/mvp-scope-and-development-plan.md](archive/mvp-scope-and-development-plan.md) | Archive | 早期 MVP 范围和开发方案，保留历史上下文 |
| [archive/mvp-business-evaluation-chain-design.md](archive/mvp-business-evaluation-chain-design.md) | Archive | 早期商业评估链路、Skill 和 Prompt 设计细节 |

## 推荐阅读路径

新开发者建议按以下顺序阅读：

1. [../README.md](../README.md)：了解项目定位、启动方式、配置、存储和代码地图。
2. [current/system-overview.md](current/system-overview.md)：理解当前整体架构和技术栈。
3. [current/evaluation-chain.md](current/evaluation-chain.md)：理解证据链、评分账本和 Gate 决策。
4. [current/domain-model.md](current/domain-model.md)：理解领域对象和 SQLite 关系表。
5. [current/frontend-architecture.md](current/frontend-architecture.md)：开发前端时阅读。
6. [current/ark-integration.md](current/ark-integration.md)：接入或调试 Ark 搜索/LLM 时阅读。

做产品或规划工作时，优先读 `product/` 和 `governance/`；做历史追溯或方案对比时，再读 `research/` 和 `archive/`。
