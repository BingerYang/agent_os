# Tasks: Agent 调度平台（可配置可扩展智能体编排系统）

**输入**: 设计文档来自 `/specs/001-agent-dispatch-platform/`
**前置**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/api.md ✅

**测试策略**: Constitution IV 要求 TDD——每个用户故事阶段先写测试（确认失败），再实现功能。

## 格式：`[ID] [P?] [Story?] 描述（文件路径）`

- **[P]**: 可并行执行（不同文件，无未完成依赖）
- **[US#]**: 对应 spec.md 中的用户故事编号

---

## Phase 1: Setup（项目脚手架）

**目的**: 初始化前后端项目结构，配置开发工具链

- [X] T001 创建后端目录结构：`backend/src/api/v1/`、`models/`、`services/`、`agents/`、`core/`、`tests/unit/`、`tests/integration/`、`tests/contract/`
- [X] T002 初始化 uv 项目：写入 `backend/pyproject.toml`（Python 3.12，声明全部后端依赖：fastapi、langchain≥1.0.0、langgraph≥1.0.0、deepagents、sqlalchemy[asyncio]、alembic、pydantic-settings、sse-starlette、aiosqlite、aiomysql、cryptography、pytest、pytest-asyncio、httpx、ruff、mypy）
- [X] T003 [P] 初始化前端项目：`pnpm create vite frontend --template vue-ts`，安装 element-plus、pinia、vue-router@4、axios，写入 `frontend/package.json`
- [X] T004 [P] 配置 ruff：在 `backend/pyproject.toml` 中添加 `[tool.ruff]` 配置（format + check，行长 120，中文注释不报错）
- [X] T005 [P] 配置 Vitest：更新 `frontend/vite.config.ts` 加入 test 配置块，创建 `frontend/vitest.config.ts`
- [X] T006 [P] 创建环境变量模板：`backend/.env.example`（DATABASE_URL、SECRET_KEY、LLM_ENCRYPTION_KEY），`frontend/.env.example`（VITE_API_BASE_URL）

**Checkpoint**: 前后端脚手架就绪，工具链可运行

---

## Phase 2: Foundational（核心基础设施）

**目的**: 数据库层、API 框架、统一响应格式——**所有用户故事均依赖此阶段**

**⚠️ CRITICAL**: 此阶段完成前不得开始任何用户故事实现

- [X] T007 [P] 实现 `backend/src/core/config.py`：pydantic-settings `Settings` 类，读取 DATABASE_URL、SECRET_KEY、LLM_ENCRYPTION_KEY、DEBUG 等环境变量
- [X] T008 实现 `backend/src/core/database.py`：SQLAlchemy 2.x async engine + `AsyncSessionLocal` + `Base`，支持 SQLite（开发）和 MySQL（生产）通过 DATABASE_URL 自动切换
- [X] T009 [P] 实现 `backend/src/core/exceptions.py`：自定义异常类（`PreCheckRejected`、`PostCheckRejected`、`SubAgentTimeout`、`ToolNotReachable`、`ResourceConflict`）
- [X] T010 [P] 实现 `backend/src/core/schemas.py`：泛型 `ApiResponse[T]` Pydantic 模型，字段：`code: int`、`message: str`、`data: T`、`timestamp: datetime`
- [X] T011 实现 `backend/src/core/middleware.py`：全局异常处理器（将所有异常统一转换为 `ApiResponse` 格式），请求日志中间件
- [X] T012 [P] 创建 ORM 模型（基础资源）：`backend/src/models/llm_model.py`（LLMModel），`backend/src/models/tool.py`（Tool），`backend/src/models/skill.py`（Skill）——含 id/created_at/updated_at 字段，参照 data-model.md
- [X] T013 [P] 创建 ORM 模型（编排实体）：`backend/src/models/agent.py`（Agent，含 agent_type ENUM），`backend/src/models/pipeline.py`（Pipeline），`backend/src/models/detection_rule.py`（DetectionRule）
- [X] T014 [P] 创建 ORM 模型（事件与关联表）：`backend/src/models/config_event.py`（ConfigChangeEvent），`backend/src/models/associations.py`（AgentTool、AgentSkill、PipelineSubAgent、PipelineDetectionRule、SkillTool 关联表）
- [X] T015 [P] 创建 `backend/src/models/__init__.py`：导出所有 ORM 模型，供 Alembic env.py 导入
- [X] T016 初始化 Alembic：在 `backend/` 执行 `alembic init alembic`，配置 `alembic/env.py` 使用 async SQLAlchemy + 导入所有 ORM models，更新 `alembic.ini` 使用 DATABASE_URL
- [X] T017 生成初始迁移：`alembic revision --autogenerate -m "initial_schema"`，验证生成的 `alembic/versions/` 迁移文件包含所有表
- [X] T018 创建 FastAPI 应用入口：`backend/src/main.py`（app 工厂、CORS 中间件、注册全局异常处理器、health 端点 `GET /health`）
- [X] T019 创建 API 路由注册：`backend/src/api/v1/router.py`（汇总所有子路由器），在 `main.py` 中注册 `/api/v1/` 前缀
- [X] T020 实现 LLMModel CRUD：`backend/src/services/llm_model_service.py`（api_key AES-256-GCM 加密/解密）+ `backend/src/api/v1/models_config.py`（GET 列表含筛选/搜索、POST、GET /{id}、PUT /{id}、DELETE /{id}），响应中 api_key 脱敏显示
- [X] T021 [P] 创建 `frontend/src/api/index.ts`：Axios 实例（baseURL = VITE_API_BASE_URL + /api/v1/），响应拦截器解包 `ApiResponse`，错误拦截器展示中文 message
- [X] T022 [P] 创建 `frontend/src/router/index.ts`：Vue Router 配置，定义全部 6 个视图路由（Workflow/MCP/Skill/Pipeline/Model/Agent）
- [X] T023 [P] 创建 `frontend/src/views/ModelView.vue`：模型配置表格 + 新建弹窗（参考 POC ModelSettings.js 布局，含供应商筛选、状态标签、API Key 密码输入框）

**Checkpoint**: `GET /health` 返回 200，`alembic upgrade head` 成功建表，ModelView 可渲染

---

## Phase 3: US1 - 单 Agent 流水线（P1）🎯 MVP

**目标**: 终端用户提交查询 → 单 Agent 完成前置检测→意图识别→工具调用→结果汇总→后置检测→返回自然语言回复

**独立测试**: `POST /api/v1/query` 携带有效 pipeline_id → 返回 answer、tool 调用记录；含违禁词的查询被前置检测拦截（返回 code=40301）；违规输出被后置检测拦截（code=40302）

### US1 测试（Constitution IV—先写测试，确认失败）

- [X] T024 [P] [US1] 写 `backend/tests/integration/test_single_agent_query.py`：测试单工具场景、多工具场景、前置检测拦截、后置检测拦截（4 个独立测试用例，运行时 MUST FAIL）
- [X] T025 [P] [US1] 写 `backend/tests/contract/test_query_contract.py`：验证 `POST /api/v1/query` 请求/响应 JSON Schema 与 contracts/api.md 一致
- [X] T026 [P] [US1] 写 `backend/tests/integration/test_detection_rules.py`：测试 keyword 规则匹配（含正则）、llm_judge 规则调用 LLM 判断
- [X] T027 [P] [US1] 写 `frontend/src/views/__tests__/WorkflowView.test.ts`：组件挂载、聊天消息发送交互

### US1 实现

- [X] T028 [P] [US1] 实现 Tool CRUD：`backend/src/services/tool_service.py` + `backend/src/api/v1/tools.py`（GET 列表含 protocol/enabled 筛选、POST、GET /{id}、PUT /{id}、DELETE /{id}、PATCH /{id}/toggle）
- [X] T029 [P] [US1] 实现 Skill CRUD：`backend/src/services/skill_service.py` + `backend/src/api/v1/skills.py`（同 tool 结构，含 tool_ids 关联）
- [X] T030 [P] [US1] 实现 Agent CRUD（SINGLE 类型）：`backend/src/services/agent_service.py` + `backend/src/api/v1/agents.py`（含 tool_ids/skill_ids 关联写入、PATCH /{id}/toggle）
- [X] T031 [US1] 实现 DetectionRule CRUD：`backend/src/services/detection_service.py` + `backend/src/api/v1/detection_rules.py`（含 stage/rule_type 筛选、PATCH /{id}/toggle）
- [X] T032 [US1] 实现 Pipeline CRUD（SINGLE_AGENT 类型）：`backend/src/services/pipeline_service.py` + `backend/src/api/v1/pipelines.py`（含 detection_rule_ids 关联、PATCH /{id}/toggle）
- [X] T033 [US1] 实现 `backend/src/agents/detection.py`：基于 LangChain 1.0 `BaseMiddleware` 的 `PreDetectionMiddleware` 和 `PostDetectionMiddleware`，调用 `detection_service` 评估规则，检测失败时抛出 `PreCheckRejected`/`PostCheckRejected`
- [X] T034 [US1] 实现 `backend/src/agents/intent_router.py`：使用 `langchain.agents.create_agent` 完成意图识别，判断查询所需工具数量（单工具/多工具），返回工具选择结果（禁止使用废弃的 `AgentExecutor` 和 `create_react_agent`）
- [X] T035 [US1] 实现 `backend/src/agents/single_agent.py`：使用 `deepagents.create_deep_agent` 创建单 Agent 实例，注册前后置检测 Middleware，封装 MCP/HTTP 工具调用，返回自然语言汇总
- [X] T036 [US1] 实现 `backend/src/services/query_service.py`：单 Agent 流水线编排——加载 Pipeline 配置 → PreDetection → intent_router → single_agent.run() → PostDetection → 构造响应
- [X] T037 [US1] 实现 `backend/src/api/v1/query.py`：`POST /api/v1/query`，支持 `stream: false`（同步响应）和 `stream: true`（SSE 流式输出，FR-010），错误统一映射到 ApiResponse 错误码
- [X] T038 [P] [US1] 创建 `frontend/src/stores/agent.ts`：Pinia store，含 agents/tools/skills/pipelines/detectionRules 的 CRUD actions
- [X] T039 [P] [US1] 创建 `frontend/src/components/common/StatusTag.vue`（启用/禁用状态标签）、`SearchBar.vue`（关键词搜索框）
- [X] T040 [P] [US1] 创建 `frontend/src/views/AgentView.vue`：Agent 管理表格（SINGLE 类型）+ 新建/编辑 Modal，含关联工具多选
- [X] T041 [US1] 创建 `frontend/src/views/WorkflowView.vue`：三栏布局（参考 POC Workflow.js）——左栏 Pipeline 配置+模型参数、中栏聊天沙盒、右栏检测规则预览，调用 `POST /api/v1/query`

**Checkpoint**: 端到端链路打通——在 WorkflowView 输入问题，系统完整走完检测→工具调用→汇总链路并返回回复

---

## Phase 4: US2 - 多 Agent 编排（P2）

**目标**: 用户提交复杂查询 → 路由至一个或多个子 Agent 并行/串行执行 → 结果聚合 → 后置检测 → 返回统一回复；子 Agent 超时时优雅降级

**独立测试**: 配置 2 个 SUB 类型子 Agent + 1 个 MULTI_AGENT Pipeline → 单子 Agent 路由（高置信度）直接转发，多子 Agent 路由串行调用后汇总；模拟子 Agent 超时触发降级响应

### US2 测试（先写测试，确认失败）

- [X] T042 [P] [US2] 写 `backend/tests/integration/test_multi_agent_query.py`：测试单子 Agent 路由（置信度≥阈值）、多子 Agent 编排、超时降级（3 个用例，运行时 MUST FAIL）
- [X] T043 [P] [US2] 写 `backend/tests/integration/test_intent_router_routing.py`：测试路由置信度计算、单/多 Agent 路由分支逻辑

### US2 实现

- [X] T044 [US2] 扩展 `backend/src/agents/intent_router.py`：添加多 Agent 路由模式——基于 LLM 判断目标子 Agent 列表 + 置信度分值，返回 `RouteResult`（target_agents、confidence、route_reason）
- [X] T045 [US2] 实现 `backend/src/agents/multi_agent.py`：用 LangGraph `StateGraph` 构建多 Agent 编排图——routing_node → [sub_agent_node_1 ... sub_agent_node_n]（并行或按 order_index 串行）→ aggregation_node；每个子 Agent 节点基于 `create_deep_agent`；`timeout_seconds` 超时触发降级（FR-009、US2-AC4）
- [X] T046 [US2] 扩展 `backend/src/services/query_service.py`：检测 pipeline_type=MULTI_AGENT 时分派到 `multi_agent.py`，复用前后置检测 Middleware
- [X] T047 [P] [US2] 扩展 `backend/src/api/v1/agents.py`：支持 agent_type=SUB 和 ORCHESTRATOR；POST `/api/v1/marketplace/agents`（第三方 Agent 注册）添加连通性验证（向 access_url 发 ping 请求）
- [X] T048 [P] [US2] 扩展 `backend/src/api/v1/pipelines.py`：支持 MULTI_AGENT 类型创建，处理 PipelineSubAgent 关联（含 order_index）和 route_confidence_threshold 字段
- [X] T049 [P] [US2] 扩展 `frontend/src/views/AgentView.vue`：增加 SUB/ORCHESTRATOR Agent 类型创建，第三方 Agent 注册表单（access_url + access_token）

**Checkpoint**: WorkflowView 选择 MULTI_AGENT Pipeline 提交查询 → 路由日志可见 → 多子 Agent 结果合并返回

---

## Phase 5: US3 - 商场式管理界面（P2）

**目标**: 运营人员在"子系统商场"浏览/搜索/筛选 Tool/Skill/Agent，安装/卸载操作后立即生效（无需重启），可注册第三方 Agent

**独立测试**: 通过 `POST /api/v1/marketplace/tool/{id}/install` 安装一个 Tool → 该 Tool 立即出现在 Agent 可用资源池；`DELETE` 卸载后不再可用；注册合法 access_url 的第三方 Agent → 出现在商场列表

### US3 测试（先写测试，确认失败）

- [X] T050 [P] [US3] 写 `backend/tests/integration/test_marketplace.py`：测试安装/卸载 Tool，安装 Skill，注册第三方 Agent（含连通性校验失败场景）
- [X] T051 [P] [US3] 写 `backend/tests/contract/test_marketplace_contract.py`：验证商场 API 请求/响应 Schema

### US3 实现

- [X] T052 [US3] 实现 `backend/src/services/marketplace_service.py`：install（更新 enabled=True）、uninstall（enabled=False）业务逻辑；第三方 Agent 连通性验证（HTTP ping）；统一商场条目聚合查询（Tool+Skill+Agent UNION）
- [X] T053 [US3] 实现 `backend/src/api/v1/marketplace.py`：`GET /marketplace`（统一列表，支持 item_type/enabled/keyword/tag 筛选）、`POST /marketplace/{item_type}/{item_id}/install`、`DELETE /marketplace/{item_type}/{item_id}/install`、`POST /marketplace/agents`（第三方注册）
- [X] T054 [P] [US3] 创建 `frontend/src/components/marketplace/MarketplaceCard.vue`：展示 Tool/Skill/Agent 卡片（名称、描述、来源平台、tags、版本、启用 Toggle），参考 POC Agents.js 卡片样式
- [X] T055 [P] [US3] 创建 `frontend/src/stores/marketplace.ts`：Pinia store，含商场列表 + install/uninstall actions
- [X] T056 [US3] 创建 `frontend/src/views/MCPView.vue`：MCP 插件广场——卡片网格布局、类型/关键词筛选栏（参考 POC Agents.js 三栏筛选）、安装/卸载 Toggle、第三方 Agent 注册入口
- [X] T057 [P] [US3] 创建 `frontend/src/views/SkillView.vue`：Skill 管理——列表 + 新建/编辑 Modal（含依赖 Tool 多选）
- [X] T058 [P] [US3] 创建 `frontend/src/views/PipelineView.vue`：前后置检测规则管理——DetectionRule 列表（含 stage/rule_type 筛选）+ 新建规则 Modal（keyword/llm_judge 类型切换表单）

**Checkpoint**: MCPView 安装/卸载子系统后，WorkflowView 的可用工具列表即时更新

---

## Phase 6: US4 - 配置变更实时生效（P3）

**目标**: 管理端任意配置变更通过 SSE 推送至运行时，运行时 10 秒内应用（不重启）；管理端不可用时运行时用缓存配置继续服务；运行时重启后从快照恢复

**独立测试**: 切换 Tool 启用状态 → SSE 流输出变更事件（时间戳差 < 10s）；断开管理端 → 查询仍正常返回；重启运行时进程 → 查询立即可用

### US4 测试（先写测试，确认失败）

- [X] T059 [P] [US4] 写 `backend/tests/integration/test_event_bus.py`：发布事件 → 订阅方收到事件、SSE 流输出格式正确、ping 保活帧
- [X] T060 [P] [US4] 写 `backend/tests/integration/test_config_cache.py`：缓存加载快照、apply_event 更新缓存、管理端下线时缓存可用（模拟 DB 不可达）、重启后重新加载

### US4 实现

- [X] T061 [US4] 实现 `backend/src/services/event_bus.py`：基于 `asyncio.Queue` 的广播事件总线——`publish(event: ConfigChangeEvent)` 写入所有订阅队列；`subscribe()` 返回异步生成器；定时发送 ping 保活帧（每 30s）
- [X] T062 [US4] 实现 `backend/src/api/v1/events.py`：`GET /api/v1/events/stream`（sse-starlette `EventSourceResponse`，连接时自动订阅事件总线）；`GET /api/v1/config/snapshot`（返回全量 agents/tools/skills/detection_rules 快照）
- [X] T063 [US4] 实现 `backend/src/services/config_cache.py`：`load_snapshot()` 从快照 API 初始化缓存；`apply_event(event)` 增量更新；`get_enabled_tools()`、`get_enabled_agents()` 等查询方法供运行时使用（禁止 DB 直连）
- [X] T064 [US4] 在各 service 写操作后接入事件发布：扩展 `marketplace_service.py`、`tool_service.py`、`skill_service.py`、`agent_service.py`、`detection_service.py`——在 enabled 状态变更后调用 `event_bus.publish(ConfigChangeEvent(...))`
- [X] T065 [US4] 重构 `backend/src/services/query_service.py` 和 `backend/src/agents/single_agent.py`/`multi_agent.py`：从 `config_cache` 获取可用工具/Agent 列表，不再直接查询数据库（满足 FR-016 解耦要求）

**Checkpoint**: 管理端切换工具状态 → SSE 流可见变更事件 → 后续查询反映新配置（无重启）

---

## Phase 7: Polish & 横切关注点

**目的**: 质量加固、mypy 合规、性能验证、文档同步

- [X] T066 [P] 补写 `backend/tests/unit/test_detection.py`：keyword 规则正则匹配单元测试、llm_judge 规则 mock LLM 调用单元测试
- [X] T067 [P] 补写 `backend/tests/unit/test_query_service.py`：query_service 路由逻辑单元测试（mock detection/single_agent/multi_agent）
- [X] T068 在 `backend/pyproject.toml` 配置 mypy，修复所有类型注解使 `mypy src/` 无报错（Constitution IV 质量门禁 #3）
- [X] T069 [P] 补写 `frontend/src/views/__tests__/MCPView.test.ts`、`SkillView.test.ts`、`PipelineView.test.ts`：Vitest 组件挂载测试
- [X] T070 [P] 确保所有 API 错误 `message` 字段使用中文（Constitution III），全局搜索英文错误消息并替换
- [X] T071 [P] 更新 `frontend/src/router/index.ts`：添加导航守卫（未配置模型时提示）、侧边栏激活状态绑定
- [X] T072 运行 `quickstart.md` 完整验证流程（5 步端到端场景）并修复发现的问题
- [X] T073 性能验证：对 `POST /api/v1/query`（单工具场景）进行压测，确认 P95 时延 ≤ 3s（SC-001）；对配置变更事件传播进行计时测试，确认 P99 ≤ 10s（SC-004）

---

## 依赖关系与执行顺序

### Phase 依赖

- **Phase 1（Setup）**: 无前置——立即开始
- **Phase 2（Foundational）**: 依赖 Phase 1 完成——**阻塞所有用户故事**
- **Phase 3（US1 P1）**: 依赖 Phase 2 完成——无其他故事依赖
- **Phase 4（US2 P2）**: 依赖 Phase 2 + Phase 3 完成（intent_router 扩展）
- **Phase 5（US3 P2）**: 依赖 Phase 2 完成——可与 Phase 4 并行
- **Phase 6（US4 P3）**: 依赖 Phase 2～5 完成（需要所有 service 层就绪才能接入事件发布）
- **Phase 7（Polish）**: 依赖所有目标故事完成

### 用户故事依赖

- **US1（P1）**: Phase 2 完成后即可开始，无故事间依赖
- **US2（P2）**: 需要 US1 的 intent_router、single_agent 基础，建议 US1 Checkpoint 后开始
- **US3（P2）**: 可与 US2 并行（不同模块：marketplace 独立于 agent 执行链路）
- **US4（P3）**: 依赖 US1～US3 全部 service 层写操作就绪（事件接入点遍布各 service）

### 各故事内部顺序

```
测试（FAIL）→ ORM/Schema → Service → API 端点 → 前端视图 → Checkpoint
```

---

## 并行执行示例

### Phase 2 并行批次

```bash
# 批次 A（可同时启动）：
T007  backend/src/core/config.py
T009  backend/src/core/exceptions.py
T010  backend/src/core/schemas.py
T012  backend/src/models/{llm_model,tool,skill}.py
T013  backend/src/models/{agent,pipeline,detection_rule}.py
T021  frontend/src/api/index.ts
T022  frontend/src/router/index.ts
T023  frontend/src/views/ModelView.vue

# 批次 B（依赖批次 A 中 T008/T015/T016）：
T016  alembic init
T018  backend/src/main.py
T019  backend/src/api/v1/router.py
```

### Phase 3（US1）并行批次

```bash
# 批次 A（测试—可并行写）：
T024  tests/integration/test_single_agent_query.py
T025  tests/contract/test_query_contract.py
T026  tests/integration/test_detection_rules.py
T027  frontend tests

# 批次 B（独立 CRUD—可并行）：
T028  Tool CRUD (service + api)
T029  Skill CRUD
T030  Agent CRUD (SINGLE)

# 批次 C（依赖批次 B）：
T031  DetectionRule CRUD
T032  Pipeline CRUD (需要 agent/tool 先就绪)
```

---

## 实施策略

### MVP（仅 US1，最快可交付）

1. 完成 Phase 1（Setup）
2. 完成 Phase 2（Foundational）——**关键路径**
3. 完成 Phase 3（US1）
4. **停止并验证**：`POST /api/v1/query` 单 Agent 端到端可用
5. 演示 / 部署

### 增量交付

```
Phase 1+2 → 基础就绪
Phase 3    → US1 可演示（MVP）
Phase 4    → 多 Agent 能力上线
Phase 5    → 商场管理 UI 上线
Phase 6    → 运行时/管理端解耦上线（生产级）
Phase 7    → 质量加固，准备生产发布
```

### 并行团队策略

```
Phase 1+2 全员协作完成
→ 开发者 A：US1（Phase 3）
→ 开发者 B：US3（Phase 5，可与 US1 并行）
→ Phase 3+5 完成后汇总
→ 开发者 A+B 协作：US2（Phase 4）
→ 全员：US4（Phase 6）+ Polish（Phase 7）
```

---

## 统计

| 阶段 | 任务数 | 用户故事 |
|------|--------|---------|
| Phase 1: Setup | 6 | — |
| Phase 2: Foundational | 17 | — |
| Phase 3: US1 (P1) | 18 | 单 Agent 流水线 🎯 MVP |
| Phase 4: US2 (P2) | 8 | 多 Agent 编排 |
| Phase 5: US3 (P2) | 9 | 商场式管理界面 |
| Phase 6: US4 (P3) | 7 | 配置变更实时生效 |
| Phase 7: Polish | 8 | 横切 |
| **合计** | **73** | **4 个用户故事** |

**并行机会**: Phase 2 中 12 个 [P] 任务；US1 中 9 个 [P] 任务；US3 与 US2 整体可并行
**MVP 范围**: Phase 1 + Phase 2 + Phase 3（41 个任务）

---

## 注意事项

- `[P]` 任务 = 不同文件、无未完成依赖，可并行执行
- `[US#]` 标签 = 任务归属的用户故事，用于追溯
- **Constitution IV 强制**: 每个故事测试任务必须先写、先确认失败，再实现
- **禁止使用废弃 API**: `AgentExecutor`、`create_react_agent`（langgraph.prebuilt）、LCEL `|` 管道语法
- **禁止在运行时直接查询 DB**（US4 以后所有新增代码均需通过 config_cache）
- 每完成一个 Checkpoint 后提交 git commit，并运行 `ruff check` + `pytest`
