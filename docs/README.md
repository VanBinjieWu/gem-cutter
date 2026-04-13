# Gem Cutter 文档目录

Gem Cutter 是一个面向“互联网热点发现、商业可行性评估、产品开发与运营管理”的一站式 Agent 项目。它参考 DeerFlow 2 的分层思想：底层保留通用 Agent Runtime，上层构建面向商业孵化的阶段化业务工作流。

## 文档清单

| 文档 | 目的 | 适用读者 |
| --- | --- | --- |
| [01-product-requirements.md](01-product-requirements.md) | 完整产品需求文档，定义目标、用户、范围、流程、验收标准 | 产品、研发、测试、业务负责人 |
| [02-overall-architecture.md](02-overall-architecture.md) | 总体技术架构、模块边界、技术栈、部署形态 | 架构师、后端、前端、DevOps |
| [03-feature-modules.md](03-feature-modules.md) | 功能点拆分与模块级需求 | 产品、研发、测试 |
| [04-agent-workflows.md](04-agent-workflows.md) | Agent 角色、阶段状态机、协作流程、评分机制 | Agent 工程、算法、产品 |
| [05-data-model.md](05-data-model.md) | 领域实体、数据表、对象存储、向量索引设计 | 后端、数据工程、测试 |
| [06-iteration-plan.md](06-iteration-plan.md) | MVP 到商业化版本的开发迭代规划 | 项目经理、研发负责人 |
| [07-risk-and-compliance.md](07-risk-and-compliance.md) | 风险、合规、安全、质量门禁与应对策略 | 产品、法务、安全、运营 |
| [08-mvp-scope-and-development-plan.md](08-mvp-scope-and-development-plan.md) | MVP 核心需求、范围控制、开发方案、验收脚本 | 产品、研发、测试、项目负责人 |
| [09-mvp-business-evaluation-chain-design.md](09-mvp-business-evaluation-chain-design.md) | MVP 商业评估链路的架构、技术、Skill 与 Prompt 设计 | Agent 工程、后端、产品、测试 |
| [10-bettafish-mirofish-reference-and-mvp-optimization.md](10-bettafish-mirofish-reference-and-mvp-optimization.md) | BettaFish/MiroFish 舆情与图谱仿真架构对标，以及 MVP 优化方案 | 架构师、Agent 工程、产品、后端 |
| [11-mvp-enhanced-design.md](11-mvp-enhanced-design.md) | 吸收 DeerFlow、BettaFish、MiroFish 后的 MVP 完善版实现蓝图 | 产品、架构师、Agent 工程、后端、前端 |
| [12-ark-responses-llm-search-integration-plan.md](12-ark-responses-llm-search-integration-plan.md) | 火山方舟 Ark Responses API、豆包内置搜索与 LLM 分析接入方案 | Agent 工程、后端、架构师 |

## 推荐阅读顺序

1. 先读 [01-product-requirements.md](01-product-requirements.md)，确认产品范围和业务目标。
2. 再读 [02-overall-architecture.md](02-overall-architecture.md)，理解系统如何落地。
3. 研发实现前细读 [03-feature-modules.md](03-feature-modules.md)、[04-agent-workflows.md](04-agent-workflows.md)、[05-data-model.md](05-data-model.md)。
4. 启动 MVP 前优先使用 [08-mvp-scope-and-development-plan.md](08-mvp-scope-and-development-plan.md) 控制第一版范围。
5. 实际开发 MVP 时，以 [11-mvp-enhanced-design.md](11-mvp-enhanced-design.md) 作为主设计入口。
6. 接入豆包模型和内置联网搜索时，阅读 [12-ark-responses-llm-search-integration-plan.md](12-ark-responses-llm-search-integration-plan.md)。
7. 实现 MVP 商业评估链路前细读 [09-mvp-business-evaluation-chain-design.md](09-mvp-business-evaluation-chain-design.md)。
8. 对标 BettaFish/MiroFish 的舆情与图谱仿真能力时，阅读 [10-bettafish-mirofish-reference-and-mvp-optimization.md](10-bettafish-mirofish-reference-and-mvp-optimization.md)。
9. 项目排期时使用 [06-iteration-plan.md](06-iteration-plan.md)。
10. 上线前使用 [07-risk-and-compliance.md](07-risk-and-compliance.md) 做发布检查。
