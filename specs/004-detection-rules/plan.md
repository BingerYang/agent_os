# Implementation Plan: Agent 检测规则引擎

**Branch**: `004-detection-rules` | **Date**: 2026-05-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/004-detection-rules/spec.md`

---

## Summary

为 AI 调度平台实现完整的检测规则引擎，在现有基础实现（`DetectionRule` 模型、keyword/llm_judge
执行引擎、CRUD API）上**增量扩展**：

1. 扩展 `DetectionRule` 模型增加 `strategy_type`（11 种）和 `action_type`（8 种）
2. 新增 `AgentDetectionBinding` 表，实现 per-agent 策略绑定 + 配置覆盖
3. 新增 `DetectionEvent` 表作为审计日志和 Review Queue
4. 新增 `PolicyConfigAudit` 表记录配置变更
5. 改造执行引擎，支持 11 种策略的独立逻辑和 8 种处置动作
6. 前端：改造检测规则管理页 + 在 AgentPage 新增"检测策略"Tab + 审计日志视图

技术选型与现有架构完全对齐（Python 3.12 / FastAPI / SQLAlchemy / React + Ant Design）。

---

## Technical Context

**Language/Version**: Python 3.12（后端）/ TypeScript + React（前端）
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0（asyncio），Alembic（迁移），Redis（限流计数器），Ant Design（前端组件）
**Storage**: MySQL 8.0（主数据）+ Redis（P-01 限流计数）
**Testing**: pytest（后端）/ Vitest（前端）
**Target Platform**: Linux server（FastAPI 管理端 + 运行时端）
**Project Type**: Web 应用（前后端分离）
**Performance Goals**: 前置策略执行 ≤200ms（不含 Agent 执行），配置热加载 ≤5s
**Constraints**: 不破坏现有 `pipeline_detection_rules` 关联；Alembic 增量迁移
**Scale/Scope**: 单 Agent 100 QPS 并发下策略无明显排队延迟

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 状态 | 说明 |
|------|------|------|
| I. RESTful 接口规范 | ✅ 合规 | 所有新增端点遵循 RESTful 规范，含 `/api/v1/` 前缀 |
| II. 技术栈合规性 | ✅ 合规 | Python 3.12 + FastAPI + SQLAlchemy + uv，前端 React + Ant Design |
| III. 中文文档优先 | ✅ 合规 | 规格/计划/任务文档全部中文 |
| IV. 测试驱动开发 | ✅ 合规 | 每个 User Story 有独立测试，后端连接真实 MySQL |
| V. 简单性优先 | ✅ 合规 | 增量扩展现有代码，不引入额外抽象层 |
| VI. 检测规则安全策略 | ✅ 合规 | 本次即为原则 VI 的具体实现 |

---

## Project Structure

### Documentation (this feature)

```text
specs/004-detection-rules/
├── plan.md              # 本文件
├── research.md          # 架构调研与技术决策
├── data-model.md        # 数据模型设计（含迁移 SQL）
├── quickstart.md        # 功能验证手册
├── contracts/
│   └── api.md           # API 接口契约
└── tasks.md             # 任务清单（由 /speckit-tasks 生成）
```

### Source Code Impact

```text
backend/src/
├── models/
│   ├── detection_rule.py         # 扩展：新增 strategy_type、action_type、max_retry_count
│   └── detection_event.py        # 新增：DetectionEvent 审计日志模型
│   └── agent_detection_binding.py# 新增：AgentDetectionBinding 绑定模型
│   └── policy_config_audit.py    # 新增：PolicyConfigAudit 配置变更审计模型
├── services/
│   ├── detection_service.py      # 扩展：新增 Agent 绑定 CRUD、事件记录方法
│   ├── detection_event_service.py# 新增：DetectionEvent 查询/复核服务
│   └── policy_audit_service.py   # 新增：审计写入辅助服务
├── agents/
│   └── detection.py              # 扩展：11 种策略执行函数 + 8 种处置动作
├── api/v1/
│   ├── detection_rules.py        # 扩展：新增 /meta 端点；兼容新字段
│   ├── agent_detection.py        # 新增：Agent 策略绑定端点
│   └── detection_events.py       # 新增：审计日志 + 复核端点
│   └── policy_audits.py          # 新增：配置变更审计端点
└── alembic/versions/
    └── xxxx_detection_rules_v2.py # 新增：4 步增量迁移

frontend/src/
├── pages/
│   ├── DetectionRulesPage.tsx    # 改造：新增 strategy_type 选择器、审计日志 Tab
│   └── AgentPage.tsx             # 扩展：新增"检测策略"Tab
├── components/
│   └── DetectionStrategyForm.tsx # 新增：策略参数动态表单组件
│   └── DetectionEventList.tsx    # 新增：审计日志列表组件
└── api/
    └── index.ts                  # 扩展：新增绑定、事件、审计 API 方法
```

---

## Complexity Tracking

> 以下为引入相对复杂度的设计点及其理由

| 设计点 | 理由 | 更简单的方案为何不够 |
|--------|------|---------------------|
| Redis 用于限流计数（P-01） | 内存滑动窗口跨进程共享，重启不丢失 | 纯内存计数在多进程/重启时无法维持状态 |
| `AgentDetectionBinding` 额外关联表 | per-agent 配置覆盖需独立存储，不能污染全局规则 | 直接在 Agent 模型存 JSON 导致规则无法复用和独立管理 |
| `DetectionEvent` 兼做 Review Queue | 减少表数量，状态字段区分 Log/Review/Escalate | 建 3 张独立表增加 JOIN 复杂度且场景高度重叠 |
| 策略函数注册表（dispatch dict） | 11 种策略执行逻辑差异大，if/else 不可维护 | 继承体系更复杂，且策略数量固定（YAGNI） |
| A-03 用外部异步队列，不用 LangGraph interrupt | deepagents 未暴露图拓扑修改 API；interrupt 需要 Checkpointer 新增持久化基础设施 | LangGraph interrupt 风险高、复杂度超出范围，详见 research.md §0 |
| P-01～A-02 用外层包裹，不用 LCEL/Callback | 外层包裹已是最优 Middleware 模式；LangChain Callbacks 无法阻断执行；LCEL 组合破坏流式事件结构 | LangChain 内置机制未提供控制流阻断能力，详见 research.md §0 |

---

## Codex Execute Command

| Task ID | File | Instruction |
|---------|------|-------------|
| T001 | `backend/alembic/versions/xxxx_detection_rules_v2.py` | 生成 Alembic 迁移脚本，按 data-model.md 中的 4 步 SQL 实现 |
| T002 | `backend/src/models/detection_rule.py` | 新增 `StrategyType`、`ActionType` 枚举和对应字段 |
| T003 | `backend/src/models/agent_detection_binding.py` | 创建 `AgentDetectionBinding` ORM 模型 |
| T004 | `backend/src/models/detection_event.py` | 创建 `DetectionEvent` ORM 模型 |
| T005 | `backend/src/models/policy_config_audit.py` | 创建 `PolicyConfigAudit` ORM 模型 |
| T006 | `backend/src/agents/detection.py` | 扩展为 11 种策略执行函数 + 策略注册表 + 8 种处置动作 |
| T007 | `backend/src/services/detection_service.py` | 新增 Agent 绑定 CRUD 和 `get_rules_for_agent` |
| T008 | `backend/src/services/detection_event_service.py` | 新建：事件记录、分页查询、复核更新服务 |
| T009 | `backend/src/api/v1/detection_rules.py` | 扩展：兼容新字段，新增 `/meta` 端点 |
| T010 | `backend/src/api/v1/agent_detection.py` | 新建：Agent 策略绑定 CRUD 端点 |
| T011 | `backend/src/api/v1/detection_events.py` | 新建：审计日志查询 + 复核端点 |
| T012 | `backend/src/api/v1/router.py` | 注册新路由 |
| T013 | `frontend/src/api/index.ts` | 新增绑定、事件、审计 API 调用方法 |
| T014 | `frontend/src/components/DetectionStrategyForm.tsx` | 策略参数动态表单（根据 strategy_type 渲染不同字段） |
| T015 | `frontend/src/components/DetectionEventList.tsx` | 审计日志列表组件（含筛选和复核操作） |
| T016 | `frontend/src/pages/DetectionRulesPage.tsx` | 改造：新增 strategy_type 字段展示/配置，新增"审计日志"Tab |
| T017 | `frontend/src/pages/AgentPage.tsx` | 新增"检测策略"Tab（含前/后置绑定列表和 per-agent 配置面板） |
| T018 | `backend/src/agents/detection_approval.py` | 新建：A-03 异步审批队列（asyncio.Event + DetectionEvent 表，write→wait→notify→resume） |
| T019 | `backend/src/services/query_service.py` | 扩展：处理 A-03 PendingApprovalResult，返回 pending 状态，SSE 推送审批完成事件 |
| T020 | `backend/tests/integration/test_detection_rules_v2.py` | 集成测试：扩展字段、Agent 绑定、事件记录、A-03 审批流程 |
