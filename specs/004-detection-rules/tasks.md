# Tasks: Agent 检测规则引擎

**Feature**: `004-detection-rules`
**Input**: `specs/004-detection-rules/`（plan.md, spec.md, data-model.md, contracts/api.md, research.md）
**Branch**: `004-detection-rules`
**Date**: 2026-05-14

**Organization**: 任务按 User Story 分组，每个 Story 可独立实现与验证。

## Format: `[ID] [P?] [Story?] 描述 + 文件路径`

- **[P]**: 可并行（不同文件，无依赖）
- **[US#]**: 所属 User Story（来自 spec.md）

---

## Phase 2: Foundational — 数据库迁移与模型扩展

**Purpose**: 所有 User Story 依赖的数据库结构，必须优先完成

**⚠️ CRITICAL**: 所有 User Story 的实现均依赖本阶段完成

- [ ] T001 生成 Alembic 增量迁移脚本：扩展 `detection_rules` 表（新增 `strategy_type`、`action_type`、`max_retry_count`），新建 `agent_detection_bindings`、`detection_events`、`policy_config_audits` 表（按 data-model.md SQL 实现）→ `backend/alembic/versions/xxxx_detection_rules_v2.py`
- [ ] T002 [P] 在 `DetectionRule` 模型中新增 `StrategyType`、`ActionType` 枚举类及 `strategy_type`、`action_type`、`max_retry_count` 字段（默认值参考 data-model.md）→ `backend/src/models/detection_rule.py`
- [ ] T003 [P] 创建 `AgentDetectionBinding` ORM 模型：含 `agent_id`、`rule_id`、`enabled`、`config_override`（JSON）、`action_override`（可空枚举）、`priority_override`（可空 INT）、UNIQUE(agent_id, rule_id) 约束 → `backend/src/models/agent_detection_binding.py`
- [ ] T004 [P] 创建 `DetectionEvent` ORM 模型：含 `agent_id`、`rule_id`、`session_id`、`stage`、`strategy_type`、`action_taken`、`hit_detail`（JSON）、`input_snapshot`（TEXT）、`output_snapshot`（TEXT 可空）、`status`（LOGGED/PENDING_REVIEW/REVIEWED/ESCALATED/RESOLVED）、复核相关字段 → `backend/src/models/detection_event.py`
- [ ] T005 [P] 创建 `PolicyConfigAudit` ORM 模型：含 `operator_id`、`agent_id`（可空）、`rule_id`、`change_type`（CREATE/UPDATE/DELETE/ENABLE/DISABLE/BIND/UNBIND）、`before_value`（JSON 可空）、`after_value`（JSON 可空）→ `backend/src/models/policy_config_audit.py`

**Checkpoint**: 迁移脚本执行 `uv run alembic upgrade head` 成功，4 张表结构与 data-model.md 一致

---

## Phase 3: US1 (P1) — 管理员 Web 端配置 Agent 检测策略

**Goal**: 管理员可在 AgentPage 的"检测策略"Tab 为 Agent 绑定策略、配置 per-agent 参数，Web 端提供策略类型的动态配置表单

**Independent Test**: 进入某 Agent 的策略配置页，启用"限流防刷"并设置 `max_requests=50`，再进另一 Agent 的同策略页，验证两者配置互相独立，均保存成功

- [ ] T006 [P] [US1] 创建 `PolicyAuditService`：实现 `record_change(operator_id, agent_id, rule_id, change_type, before, after)` 异步写入 `policy_config_audits` 表 → `backend/src/services/policy_audit_service.py`
- [ ] T007 [US1] 扩展 `DetectionService`：新增 `create_binding`、`update_binding`、`delete_binding`、`get_bindings_for_agent`、`get_binding_summary`、`get_rules_for_agent`（返回合并后生效配置：`{**rule.rule_content, **(binding.config_override or {})}`）方法；每次绑定变更后调用 `PolicyAuditService.record_change` → `backend/src/services/detection_service.py`
- [ ] T008 [US1] 扩展 `detection_rules` 路由：兼容请求/响应中的 `strategy_type`、`action_type`、`max_retry_count` 新字段；新增 `GET /detection-rules/meta` 端点，返回 11 种策略类型元信息（含 `config_schema`）和 8 种处置动作枚举（按 contracts/api.md §五实现）→ `backend/src/api/v1/detection_rules.py`
- [ ] T009 [US1] 创建 `agent_detection` 路由：实现 `GET/POST /agents/{agent_id}/detection-bindings`、`PUT/DELETE /agents/{agent_id}/detection-bindings/{binding_id}`、`PATCH /agents/{agent_id}/detection-bindings/{binding_id}/toggle`、`GET /agents/{agent_id}/detection-bindings/summary` 共 6 个端点（按 contracts/api.md §二实现，响应含 `effective_config` 合并结果）→ `backend/src/api/v1/agent_detection.py`
- [ ] T010 [US1] 在路由注册文件中引入并注册 `agent_detection` router（prefix `/api/v1`）→ `backend/src/api/v1/router.py`
- [ ] T011 [P] [US1] 扩展前端 API 模块：新增 `getAgentDetectionBindings`、`createBinding`、`updateBinding`、`deleteBinding`、`toggleBinding`、`getBindingSummary`、`getDetectionRulesMeta` 等方法 → `frontend/src/api/index.ts`
- [ ] T012 [P] [US1] 创建 `DetectionStrategyForm` 组件：根据传入的 `strategy_type` 值动态渲染对应配置字段（如 `rate_limit` 渲染 `window_seconds`/`max_requests`/`key_by`，`content_filter` 渲染 `sub_types` 多选框），配置项说明和默认值从 `/detection-rules/meta` 接口获取 → `frontend/src/components/DetectionStrategyForm.tsx`
- [ ] T013 [US1] 在 `AgentPage` 中新增"检测策略"Tab：分前置/后置两组展示绑定列表；支持绑定新策略、修改 per-agent 配置（嵌入 `DetectionStrategyForm`）、解绑、启用/禁用操作；展示 `effective_config` 和 `effective_action`（按 contracts/api.md §二 summary 格式）→ `frontend/src/pages/AgentPage.tsx`

**Checkpoint**: 管理员可在 AgentPage 成功绑定并配置策略，两个 Agent 的同策略配置相互独立，`/agents/{id}/detection-bindings/summary` 返回正确的生效配置

---

## Phase 4: US2 (P1) — 前置策略自动拦截/处置不合规请求

**Goal**: `run_pre_detection` 能按优先级依次执行 Agent 绑定的 P-01～P-08 策略，并按 `action_type` 执行对应处置动作（block/rewrite/log_review/retry/log_only/degrade/escalate/alert）

**Independent Test**: 在测试 Agent 上绑定"限流防刷"策略（`max_requests=1`，`window_seconds=60`），连续调用 2 次，验证第 2 次返回限流错误，`detection_events` 表有对应命中记录

- [ ] T014 [US2] 扩展 `detection.py` 前置策略执行引擎：为 P-01～P-08 实现独立执行函数（P-01 使用 Redis 滑动窗口；P-02 复用鉴权中间件；P-03 关键词+可选 LLM；P-04 正则+可选 LLM；P-05 PII 正则替换；P-06 LLM 意图判断；P-07 角色权限矩阵；P-08 内置规则组合），建立 `STRATEGY_REGISTRY: dict[StrategyType, Callable]`，更新 `run_pre_detection` 使用注册表 dispatch；每次命中后调用 `DetectionEvent` 写入审计（`strategy_type`、`action_taken`、`hit_detail`）→ `backend/src/agents/detection.py`

**Checkpoint**: P-03 违规内容拦截命中后立即短路，`detection_events` 表有记录；P-05 改写后明文不流转至 Agent

---

## Phase 5: US3 (P2) — 后置策略校验 Agent 响应

**Goal**: Agent 生成响应后，`run_post_detection` 执行 A-01 隐私脱敏、A-02 业务规则校验、A-03 人机审批，并按处置动作执行（改写/重试/escalate 等）

**Independent Test**: 在测试 Agent 上绑定"后置隐私防泄密"策略（`pii_types=["phone"]`，`action=rewrite`），构造会触发手机号输出的提示词，验证调用方收到的响应中手机号已脱敏为 `***`

- [ ] T015 [US3] 扩展 `detection.py` 后置策略：为 A-01（PII 输出脱敏）和 A-02（业务结果规则校验，支持 `retry` action + 兜底响应）实现执行函数，注册到 `STRATEGY_REGISTRY`，更新 `run_post_detection` 使用注册表 dispatch → `backend/src/agents/detection.py`
- [ ] T016 [US3] 创建 A-03 异步审批队列：实现 `ApprovalQueue`（内存 `dict[str, asyncio.Event]`）和 `create_approval_event`（写入 `DetectionEvent(status=ESCALATED)`）、`wait_for_approval(event_id, timeout_seconds)`（阻塞等待 `asyncio.Event`）、`resolve_approval(event_id, approved)` 三个函数；超时后按 `fallback_action` 执行兜底处置 → `backend/src/agents/detection_approval.py`
- [ ] T017 [US3] 扩展 `query_service.py`：在 `run_post_detection` 返回 A-03 `PendingApprovalResult` 时，将调用方状态置为 `pending_approval`（SSE 推送 `status=pending`）；审批通过后通过 `asyncio.Event` 恢复，将最终响应推送给调用方 → `backend/src/services/query_service.py`

**Checkpoint**: A-03 绑定后，Agent 响应被阻塞，调用方收到 `pending_approval` 状态；调用 review 接口 `PATCH /detection-events/{id}/review` 后，调用方收到最终响应

---

## Phase 6: US4 (P2) — 审计员查看策略命中与处置记录

**Goal**: 审计员可在 Web 端查看所有策略命中事件，按 Agent/策略/处置动作/时间段筛选，并对 `PENDING_REVIEW`/`ESCALATED` 条目进行人工复核

**Independent Test**: 触发 3 次违规内容拦截后，进入审计日志页，验证每条记录含 Agent 名称、策略名称、处置结果、触发时间，且支持按 `strategy_type=content_filter` 过滤

- [ ] T018 [P] [US4] 创建 `DetectionEventService`：实现 `record_event`（写入 `detection_events`）、`list_events`（分页查询，支持 `agent_id`/`strategy_type`/`action_taken`/`status`/`stage`/`start_time`/`end_time` 过滤）、`get_event`（单条详情）、`review_event`（更新 status 和 reviewer 信息，仅 PENDING_REVIEW/ESCALATED 可操作）→ `backend/src/services/detection_event_service.py`
- [ ] T019 [P] [US4] 创建 `policy_audits` 路由：实现 `GET /policy-config-audits`（分页查询，支持 `agent_id`/`rule_id`/`change_type`/`operator_id`/时间范围过滤，按 contracts/api.md §四实现）→ `backend/src/api/v1/policy_audits.py`
- [ ] T020 [US4] 创建 `detection_events` 路由：实现 `GET /detection-events`（分页查询）、`GET /detection-events/{event_id}`（详情）、`PATCH /detection-events/{event_id}/review`（提交复核）三个端点（按 contracts/api.md §三实现）→ `backend/src/api/v1/detection_events.py`
- [ ] T021 [US4] 在路由注册文件中引入并注册 `detection_events` 和 `policy_audits` router → `backend/src/api/v1/router.py`
- [ ] T022 [P] [US4] 创建 `DetectionEventList` 组件：展示事件列表（含 Agent 名称、策略、处置动作、状态列）；支持 `agent_id`/`strategy_type`/`action_taken`/`status`/时间范围筛选；对 PENDING_REVIEW/ESCALATED 条目提供"标注已复核"按钮调用 review 接口 → `frontend/src/components/DetectionEventList.tsx`
- [ ] T023 [US4] 在 `DetectionRulesPage` 中新增"审计日志"Tab：嵌入 `DetectionEventList` 组件，展示全量命中事件；新增"配置变更审计"Tab，展示 `policy_config_audits` 数据 → `frontend/src/pages/DetectionRulesPage.tsx`

**Checkpoint**: `GET /detection-events?strategy_type=content_filter` 只返回内容过滤事件；PATCH review 接口可将 PENDING_REVIEW 状态更新为 REVIEWED

---

## Phase 7: US5 (P3) — 管理员设置全局默认策略配置

**Goal**: 管理员可在检测规则管理页查看/创建/编辑全局策略模板，含 `strategy_type` 选择器和对应配置表单；未单独配置的 Agent 自动继承全局默认值

**Independent Test**: 在全局配置将"限流防刷"默认阈值设为 100，新建 Agent 不单独配置该策略，调用 `GET /agents/{id}/detection-bindings/summary` 验证 `effective_config.max_requests = 100`

- [ ] T024 [US5] 改造 `DetectionRulesPage` 策略模板管理视图：在新建/编辑规则表单中新增 `strategy_type` 选择器（从 `/detection-rules/meta` 获取选项）；选择类型后动态嵌入 `DetectionStrategyForm` 展示对应配置字段；在列表视图增加 `strategy_type` 和 `action_type` 列展示 → `frontend/src/pages/DetectionRulesPage.tsx`

**Checkpoint**: 管理员可选择 `rate_limit` 类型创建全局规则，配置字段正确显示；全局规则对未绑定该 Agent 的调用返回正确 effective_config 默认值

---

## Phase 8: Polish & 集成测试

**Purpose**: 端到端验证所有 User Story、回归现有测试

- [ ] T025 [P] 编写集成测试：覆盖模型扩展字段、Agent 绑定 CRUD、`get_rules_for_agent` 合并逻辑、P-01 限流计数、P-05 PII 脱敏改写、A-03 审批等待→恢复完整流程、DetectionEvent 写入验证 → `backend/tests/integration/test_detection_rules_v2.py`
- [ ] T026 按 `quickstart.md` Step 1-6 顺序执行验证，确认全部通过；回归运行 `uv run pytest tests/ -k "detection" -v`，确认已有检测测试零回归

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: 无依赖，立即开始 — **BLOCKS 所有 User Story**
- **US1 (Phase 3)**: 依赖 Phase 2（T001-T005 全部完成）
- **US2 (Phase 4)**: 依赖 Phase 2；与 US1 可并行（不同文件）
- **US3 (Phase 5)**: 依赖 Phase 2；依赖 T015 在 Phase 4 中完成（共享 detection.py）
- **US4 (Phase 6)**: 依赖 Phase 2；T018 可在 US2/US3 之前并行；T023 依赖 T022
- **US5 (Phase 7)**: 依赖 US1（T012 DetectionStrategyForm 已存在）
- **Polish (Phase 8)**: 依赖所有目标 Story 完成

### 同 Phase 内依赖

| Phase 3 (US1) | 依赖关系 |
|----------------|---------|
| T006, T008, T011, T012 | 可并行（不同文件）|
| T007 | 依赖 T006（PolicyAuditService 需先存在）|
| T009 | 依赖 T007（服务层先于路由）|
| T010 | 依赖 T009（路由文件需先创建）|
| T013 | 依赖 T011, T012（frontend API + Form 先完成）|

| Phase 5 (US3) | 依赖关系 |
|----------------|---------|
| T015 | 依赖 T014（在 US2 的 detection.py 上继续扩展）|
| T016 | 可与 T015 并行（新文件）|
| T017 | 依赖 T016（query_service 需要 ApprovalQueue）|

| Phase 6 (US4) | 依赖关系 |
|----------------|---------|
| T018, T019, T022 | 可并行（不同文件）|
| T020 | 依赖 T018（服务层先于路由）|
| T021 | 依赖 T020, T019（路由注册依赖文件创建）|
| T023 | 依赖 T022（嵌入 DetectionEventList 组件）|

---

## Parallel Opportunities

### Phase 2: 全部并行（5 个不同文件）

```
并行启动：
  Task: "T002 扩展 detection_rule.py 模型"
  Task: "T003 创建 agent_detection_binding.py 模型"
  Task: "T004 创建 detection_event.py 模型"
  Task: "T005 创建 policy_config_audit.py 模型"
（T001 迁移脚本可在模型完成后并行补充，或在全部模型完成后最后生成）
```

### Phase 3 (US1): 前 4 个任务并行

```
并行启动（阶段一）：
  Task: "T006 创建 policy_audit_service.py"
  Task: "T008 扩展 detection_rules.py API"
  Task: "T011 扩展 frontend api/index.ts"
  Task: "T012 创建 DetectionStrategyForm.tsx"

顺序执行（阶段二，依赖阶段一）：
  Task: "T007 扩展 detection_service.py"（依赖 T006）
  Task: "T009 创建 agent_detection.py API"（依赖 T007）
  Task: "T010 注册路由 router.py"（依赖 T009）
  Task: "T013 AgentPage 检测策略 Tab"（依赖 T011, T012）
```

### Phase 6 (US4): 服务层和前端组件并行

```
并行启动：
  Task: "T018 创建 detection_event_service.py"
  Task: "T019 创建 policy_audits.py API"
  Task: "T022 创建 DetectionEventList.tsx"
```

---

## Implementation Strategy

### MVP（只交付 US1 + US2）

1. 完成 Phase 2: Foundational（T001-T005）
2. 完成 Phase 3: US1（T006-T013）
3. 完成 Phase 4: US2（T014）
4. **STOP & VALIDATE**: 管理员可配置策略，限流/内容拦截/PII 脱敏正常工作
5. 可上线演示核心安全保护能力

### 完整交付顺序

1. Phase 2 → Phase 3 → Phase 4（US1 + US2，P1 完整交付）
2. Phase 5 → Phase 6（US3 + US4，P2 后置保护 + 审计能力）
3. Phase 7（US5，P3 全局配置运营效率优化）
4. Phase 8（集成测试 + 回归验证）

---

## Notes

- [P] = 不同文件，可并行执行
- [US#] 标签追踪任务到 spec.md 中的具体 User Story
- T014 和 T015 修改同一文件 `detection.py`，必须严格顺序执行（T014 先、T015 后）
- T023 和 T024 修改同一文件 `DetectionRulesPage.tsx`，T023（US4 审计 Tab）应先于 T024（US5 策略选择器）
- T010 和 T021 均修改 `router.py`，应在对应路由文件创建完成后再执行
- 集成测试（T025）必须连接真实 MySQL，不使用 mock（参见项目 Constitution §IV）
- Redis 依赖：P-01 限流在测试环境需要 Redis 实例可用
