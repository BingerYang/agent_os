# 实现计划：Agent 调度平台（可配置可扩展智能体编排系统）

**分支**: `001-agent-dispatch-platform` | **日期**: 2026-04-18 | **规格**: [spec.md](./spec.md)
**输入**: `/specs/001-agent-dispatch-platform/spec.md`

## 摘要

构建一套可配置、可扩展的 Agent 调度平台：统一入口处理用户自然语言查询，支持单 Agent（工具调度）与多 Agent（子 Agent 编排）两条流水线；运营人员通过商场式管理界面插拔式配置 MCP 工具、技能、Agent；运行时与管理端通过订阅通知机制解耦，支持未来分离部署。

技术方案：后端采用 FastAPI + LangChain ≥ 1.0.0（2025-10-22 发布，`create_agent` + Middleware 体系）+ DeepAgents（LangChain 官方团队构建于 LangGraph 之上的高级 Agent harness，`create_deep_agent`），前端采用 Vue 3 + Element Plus + Vite，数据库开发阶段使用 SQLite（生产切换 MySQL 8.0+），运行时/管理端通过 SSE 内部事件总线通信。

## 技术上下文

**语言/版本**: Python 3.12（后端，uv 管理）/ Node.js 20+（前端构建）
**主要依赖**:
- 后端：FastAPI、`langchain ≥ 1.0.0`、`langgraph ≥ 1.0.0`、`deepagents`（PyPI 公开包，`uv add deepagents`）、SQLAlchemy 2.x、Alembic、Pydantic v2、sse-starlette
- 前端：Vue 3（Composition API）、Element Plus、Vite、Pinia、Vue Router 4、Axios
- **注意**：禁止使用 `AgentExecutor`、`create_react_agent`（langgraph.prebuilt）和 LCEL 管道语法（`|`），均已在 LangChain 1.0 中废弃

**存储**: SQLite（开发阶段） → MySQL 8.0+（生产，同 ORM 层，切换仅需配置）
**测试**: pytest（后端，含真实 DB 集成测试）/ Vitest（前端）
**目标平台**: Linux 服务器（Docker 容器化）/ 现代浏览器
**项目类型**: Web 应用（全栈，前后端分离）
**性能目标**:
- 单工具场景端到端时延 P95 ≤ 3 秒
- 多工具/多 Agent 场景端到端时延 P95 ≤ 10 秒
- 配置变更管理端保存 → 运行时感知 P99 ≤ 10 秒

**约束**: 运行时禁止直接访问数据库；管理端不可用时运行时使用缓存配置继续服务（可用率 ≥ 99%）
**规模/范围**: 同时接入 ≤ 50 个子系统（工具+技能+Agent 合计）

## Constitution Check

*GATE：Phase 0 研究前必须通过。Phase 1 设计后重新校验。*

| 原则 | 状态 | 说明 |
|------|------|------|
| I. RESTful 接口规范 | ✅ 合规 | 所有路由在 `/api/v1/` 下，标准 HTTP 方法和状态码，响应体含 `code/message/data/timestamp` |
| II. 技术栈合规性 | ✅ 合规（含例外） | Python 3.12/FastAPI/LangChain ≥ 1.0.0/deepagents/MySQL 全部采用；开发阶段 SQLite 为已记录例外 |
| III. 中文文档优先 | ✅ 合规 | 所有规格/计划/任务文档使用中文，业务逻辑注释使用中文 |
| IV. 测试驱动开发 | ✅ 合规 | 先写测试；pytest 集成测试连接真实数据库；覆盖率目标 ≥ 80% |
| V. 简单性优先（YAGNI） | ✅ 合规（含例外） | 运行时/管理端解耦为明确需求（FR-015/FR-016）非过度设计；已在复杂度跟踪中记录 |

**Post-Design 重新校验**：Phase 1 完成后更新本节。

## 项目结构

### 规格文档（本功能）

```text
specs/001-agent-dispatch-platform/
├── plan.md              # 本文件
├── research.md          # Phase 0 输出
├── data-model.md        # Phase 1 输出
├── quickstart.md        # Phase 1 输出
├── contracts/           # Phase 1 输出
│   └── api.md
└── tasks.md             # Phase 2 输出（/speckit-tasks 生成）
```

### 源代码（仓库根目录）

```text
backend/
├── src/
│   ├── api/
│   │   └── v1/
│   │       ├── query.py           # 查询统一入口（FR-001）
│   │       ├── agents.py          # Agent CRUD
│   │       ├── tools.py           # Tool CRUD
│   │       ├── skills.py          # Skill CRUD
│   │       ├── pipelines.py       # Pipeline CRUD
│   │       ├── detection_rules.py # 前置/后置检测规则 CRUD
│   │       ├── marketplace.py     # 商场浏览/安装/卸载
│   │       ├── models_config.py   # 模型配置 CRUD
│   │       └── events.py          # SSE 订阅推送端点（FR-015）
│   ├── models/
│   │   ├── agent.py
│   │   ├── tool.py
│   │   ├── skill.py
│   │   ├── pipeline.py
│   │   ├── detection_rule.py
│   │   └── config_event.py
│   ├── services/
│   │   ├── query_service.py       # 查询流水线调度
│   │   ├── marketplace_service.py # 商场安装/卸载业务逻辑
│   │   ├── event_bus.py           # 内部 SSE 事件总线
│   │   └── config_cache.py        # 运行时配置缓存（FR-016）
│   ├── agents/
│   │   ├── single_agent.py        # 单 Agent 流水线：deepagents.create_deep_agent（FR-005/FR-006）
│   │   ├── multi_agent.py         # 多 Agent 编排：LangGraph StateGraph + 多个 create_deep_agent 节点（FR-007～FR-009）
│   │   ├── intent_router.py       # 意图路由：langchain.agents.create_agent（FR-002/FR-007）
│   │   └── detection.py           # 前置/后置检测：LangChain 1.0 BaseMiddleware 子类（FR-003/FR-004）
│   └── core/
│       ├── config.py
│       ├── database.py
│       ├── middleware.py
│       └── exceptions.py
├── tests/
│   ├── unit/
│   ├── integration/               # 连接真实数据库（Constitution IV）
│   └── contract/
└── pyproject.toml                 # uv 依赖声明

frontend/
├── src/
│   ├── components/
│   │   ├── common/               # 通用组件（SearchBar、StatusTag、MarketplaceCard）
│   │   └── marketplace/
│   ├── views/
│   │   ├── WorkflowView.vue      # Agent 工作流编排（参考 POC Workflow.js 三栏布局）
│   │   ├── MCPView.vue           # MCP 插件广场（参考 POC Agents.js 卡片网格）
│   │   ├── SkillView.vue         # Skill 管理
│   │   ├── PipelineView.vue      # 前后置检测规则管理
│   │   ├── ModelView.vue         # 模型配置（参考 POC ModelSettings.js 表格+弹窗）
│   │   └── AgentView.vue         # Agent 配置管理
│   ├── stores/
│   │   ├── agent.ts
│   │   ├── marketplace.ts
│   │   └── config.ts
│   ├── api/
│   │   └── index.ts              # Axios 封装，对齐 /api/v1/ 路径
│   └── router/
│       └── index.ts
└── vite.config.ts
```

**结构决策**：前后端分离 Web 应用（Option 2）。前端独立部署，通过 `/api/v1/` RESTful 接口通信；运行时 SSE 端点（`/api/v1/events/stream`）供管理端和运行时内部订阅配置变更。

## 复杂度跟踪

| 违反原则 | 为何必要 | 拒绝更简方案的理由 |
|---------|---------|-----------------|
| SQLite 用于开发（Constitution II 要求 MySQL 8.0+） | 降低本地开发环境搭建成本；开发/测试阶段无需 MySQL 服务 | 同一 SQLAlchemy ORM 层，切换仅改 `DATABASE_URL` 环境变量，零代码改动 |
| 运行时/管理端 SSE 事件总线（额外抽象层） | FR-015/FR-016 明确要求：运行时不直接访问数据库，配置变更 ≤ 10s 生效 | 直接 DB 轮询违反解耦架构目标；SSE 是最简实现，V1 无需外部消息队列（Redis/NATS） |

## Codex 执行命令

| Task ID | 文件 | 指令 |
|---------|------|------|
| T-001 | `backend/pyproject.toml` | 初始化 uv 项目，Python 3.12，声明全部后端依赖 |
| T-002 | `backend/src/core/database.py` | SQLAlchemy async engine，DATABASE_URL 从环境变量读取，支持 SQLite/MySQL |
| T-003 | `backend/src/services/event_bus.py` | 内存 SSE 事件总线：publish(event) 和 subscribe() 异步接口 |
| T-004 | `frontend/vite.config.ts` | Vue 3 + Element Plus Vite 配置，代理 /api 到后端 |
