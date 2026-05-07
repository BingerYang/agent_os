# Tasks: Backend 管理端/运行时拆分与 Agent 编排池化重构

**输入**: 设计文档来自 `specs/003-backend-split-runtime/`  
**前置**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/api.md ✅

**测试策略**: Constitution IV 要求 TDD——每个用户故事阶段先写测试（确认失败），再实现功能。

## 格式：`[ID] [P?] [Story?] 描述（文件路径）`

- **[P]**: 可并行执行（不同文件，无未完成依赖）
- **[US#]**: 对应 spec.md 中的用户故事编号

---

## Phase 1: Setup（基础设施扩展）

**目的**: 新增依赖、数据库模型与迁移——所有用户故事均依赖此阶段

**⚠️ CRITICAL**: 此阶段完成前不得开始任何用户故事实现

- [ ] T001 在 `backend/pyproject.toml` 中新增 `redis[asyncio]>=5.0.0` 依赖，并添加 `REDIS_URL`、`REDIS_STREAM_KEY`、`RUNTIME_AGENT_LOAD_MODE`、`RUNTIME_AGENT_POOL_MAX_SIZE` 到 `backend/src/core/config.py` 的 Settings 类
- [ ] T002 [P] 新增 `AgentPublish` ORM 模型至 `backend/src/models/agent_publish.py`（字段：id、agent_id、version、config_snapshot JSON、is_active、published_at、published_by、created_at、updated_at；含 `(agent_id, is_active)` 联合索引；参照 data-model.md）
- [ ] T003 [P] 修改 `backend/src/models/agent.py`，新增 `published_version`（INT NULL）和 `last_published_at`（DATETIME NULL）两个字段
- [ ] T004 更新 `backend/src/models/__init__.py`，导出 `AgentPublish`
- [ ] T005 生成 Alembic 迁移脚本：`alembic revision --autogenerate -m "add_agent_publish_table_and_agent_publish_fields"`，验证生成的迁移文件包含 `agent_publishes` 表和 `agents` 表的两个新列
- [ ] T006 执行 `alembic upgrade head` 并验证 `agent_publishes` 表已创建

**Checkpoint**: `agent_publishes` 表已存在，`agents` 表新增字段就绪

---

## Phase 2: Foundational（运行时核心基础）

**目的**: 构建抽象基类、池管理器、RuntimeContext——所有运行时用户故事均依赖此阶段

**⚠️ CRITICAL**: Phase 3/4/5 不得在此阶段完成前开始

- [ ] T007 实现 `backend/src/agents/base.py`：定义 `BaseNode`（ABC，含 `execute(context: AgentContext) -> AgentResult` 和 `stream(context: AgentContext) -> AsyncIterator[StreamEvent]` 抽象方法）、`AgentContext`（dataclass，含 query/session_id/pipeline_config/agent_pool/tool_pool/mcp_pool）、`AgentResult`（dataclass，含 answer/tools_called/session_id/latency_ms/pipeline_type/sub_results）、`StreamEvent`（dataclass，含 type/content/tool/output/message/answer/tools_called/session_id/latency_ms）；所有类含完整类型注解和 Google 风格 docstring
- [ ] T008 [P] 实现 `backend/src/agents/pool/mcp_pool.py`：`MCPEntry` dataclass（session/lock/endpoint_url/headers/connected_at/last_used_at/is_healthy）；`MCPConnectionPool` 类，含 `get_or_create(endpoint_url, headers) -> MCPEntry`、`call_tool(endpoint_url, tool_name, args) -> str`（内部 `async with entry.lock` 串行化）、`ensure_connected(entry)`（自动重连）、`close_all()` 方法；Google docstring + 完整类型注解
- [ ] T009 [P] 实现 `backend/src/agents/strategies/base.py`：`BaseToolStrategy`（ABC，含 `execute(tool_config, kwargs) -> str` 抽象方法）；实现 `backend/src/agents/strategies/mcp_strategy.py`（`MCPToolStrategy`，从现有 `single_agent.py` 迁移 MCP 调用逻辑，注入 MCPConnectionPool）；实现 `backend/src/agents/strategies/http_strategy.py`（`HTTPToolStrategy`，从现有 `single_agent.py` 迁移 HTTP 调用逻辑）
- [ ] T010 [P] 实现 `backend/src/agents/pool/tool_pool.py`：`ToolPoolEntry` dataclass；`ToolPool` 类，含 `build_from_snapshot(snapshot_tools, mcp_pool) -> None`（从 config_snapshot 构建 LangChain StructuredTool，MCP 工具使用 MCPToolStrategy）、`get(tool_id) -> ToolPoolEntry | None`、`get_lc_tools(tool_ids) -> list[StructuredTool]`、`invalidate(tool_id)`；Google docstring
- [ ] T011 [P] 实现 `backend/src/agents/pool/skill_pool.py`：`SkillPoolEntry` dataclass；`SkillPool` 类，含 `build_from_snapshot(snapshot_skills) -> None`、`get(skill_id) -> SkillPoolEntry | None`、`invalidate(skill_id)`；Google docstring
- [ ] T012 实现 `backend/src/agents/pool/agent_pool.py`：`AgentPoolEntry` dataclass（含 agent_id/version/agent_type/compiled_graph/lc_tools/system_prompt/llm_config/sub_agent_ids/route_confidence_threshold/timeout_seconds/loaded_at/last_accessed_at/access_count）；`AgentPool` 类，含 `build_entry(publish_snapshot, tool_pool, mcp_pool) -> AgentPoolEntry`（调用 `create_deep_agent`）、`get(agent_id) -> AgentPoolEntry | None`（更新 last_accessed_at 和 access_count）、`upsert(entry)`（若池满则先 `evict_one`）、`evict_one() -> int`（评分公式 `0.3×age_hours + 0.7×idle_hours`，淘汰最高分，记录结构化日志）、`on_eviction(event: AgentEvictionEvent)` hook（空实现，供 V2 告警扩展）；Google docstring + 完整类型注解
- [ ] T013 实现 `backend/src/runtime/context.py`：`RuntimeContext` 单例 dataclass，持有 `agent_pool: AgentPool`、`tool_pool: ToolPool`、`skill_pool: SkillPool`、`mcp_pool: MCPConnectionPool`、`pipeline_cache: dict[str, PipelineCacheEntry]`、`detection_cache: dict[int, DetectionRule]`；`PipelineCacheEntry` dataclass（pipeline_uid/pipeline_id/pipeline_type/primary_agent_id/detection_rule_ids/route_confidence_threshold/timeout_seconds/enabled）；Google docstring
- [ ] T014 实现 `backend/src/runtime/loader.py`：`load_from_db(db: AsyncSession) -> RuntimeContext`（从数据库全量加载：enabled pipelines + detection rules + AgentPublish is_active=True，填充所有池；DB 不可用时抛出异常，**不降级**）；`start_redis_subscriber(context: RuntimeContext, redis_url: str, stream_key: str) -> asyncio.Task`（XREAD 从 `$` 开始，后台 Task；事件处理：按 agent_id 分组取 max publish_id，DB 获取 config_snapshot，调用 pool upsert）；`stop_redis_subscriber(task: asyncio.Task)`；Google docstring + 完整类型注解

**Checkpoint**: 所有池管理器、RuntimeContext、Loader 可独立实例化和测试

---

## Phase 3: US1 - 管理端独立部署并通过 Redis Stream 发布 Agent 变更（P1）

**目标**: 运营人员通过 `PATCH /api/v1/agents/{id}/publish` 发布 Agent，写库 + Redis Stream 推送；管理端可在不启动运行时的情况下独立运行。

**独立测试**: 仅启动管理端服务，完成发布请求，验证 `agent_publishes` 表出现记录、Redis Stream 出现事件、操作成功返回 `publish_id`。

### US1 测试（TDD—先写测试，确认失败）

- [ ] T015 [P] [US1] 写 `backend/tests/integration/test_publish_agent.py`：测试 `PATCH /agents/{id}/publish`：成功发布创建 AgentPublish 记录、版本递增、redis_notified 字段；Redis 不可用时返回 code=0 + redis_notified=false；Agent 不存在返回 40401；Agent 无 LLM 模型返回 50001（TDD：运行确认 FAIL）
- [ ] T016 [P] [US1] 写 `backend/tests/integration/test_agent_publish_history.py`：测试 `GET /agents/{id}/publishes` 返回历史列表、分页（TDD：FAIL）

### US1 实现

- [ ] T017 [US1] 实现 `backend/src/services/publish_service.py`：`publish_agent(db: AsyncSession, agent_id: int) -> PublishResult`（序列化完整 config_snapshot、写 `AgentPublish`、更新旧记录 is_active=False、更新 `agents.published_version`、向 Redis Stream XADD 推送事件 `{publish_id, agent_id, version, timestamp}`；Redis 失败不回滚，返回 `redis_notified=False`）；`PublishResult` dataclass；Google docstring
- [ ] T018 [US1] 修改 `backend/src/api/v1/agents.py`：新增 `PATCH /{id}/publish` 端点（调用 `publish_service.publish_agent`，返回 `ApiResponse[PublishResult]`）；新增 `GET /{id}/publishes` 端点（返回 AgentPublish 历史列表，按 version 降序）
- [ ] T019 [US1] 新增 `backend/src/main_management.py`：创建管理端 FastAPI 应用，lifespan 仅含 `init_db()`，路由注册所有现有管理端 CRUD 路由（agents/tools/skills/pipelines/mcp_servers/detection_rules/models_config/marketplace/events），**不含 query 路由**；`GET /health` 端点返回 `{"status": "ok"}`

**Checkpoint**: `PATCH /agents/{id}/publish` 正常响应；管理端可独立 `uvicorn src.main_management:app` 启动

---

## Phase 4: US2 - 运行时订阅 Redis Stream 并热加载已发布 Agent（P1）

**目标**: 运行时启动时从 DB 加载 Agent 配置，持续订阅 Redis Stream，管理端发布后 10 秒内完成热加载。

**独立测试**: 启动运行时服务（`uvicorn src.main_runtime:app`），验证 `/health` 返回 `agents_loaded` 字段；发布新 Agent 后，10 秒内 query 接口使用新配置响应。

### US2 测试（TDD—先写测试，确认失败）

- [ ] T020 [P] [US2] 写 `backend/tests/integration/test_loader.py`：测试 `load_from_db` 填充 RuntimeContext（pipeline_cache、detection_cache、agent_pool 非空）；测试 DB 不可用时 `load_from_db` 抛出异常（not silenced）；测试 Redis 事件触发 agent_pool 热更新（TDD：FAIL）
- [ ] T021 [P] [US2] 写 `backend/tests/unit/test_agent_pool.py`：测试 `AgentPool.get` 更新 last_accessed_at；测试 `evict_one` 淘汰评分最高条目并记录日志；测试 `on_eviction` hook 调用（TDD：FAIL）

### US2 实现

- [ ] T022 [US2] 新增 `backend/src/main_runtime.py`：创建运行时 FastAPI 应用；lifespan 中调用 `load_from_db`（DB 不可用则服务启动失败，不降级）、`start_redis_subscriber`（后台 Task），shutdown 时 `stop_redis_subscriber` + `mcp_pool.close_all()`；路由仅注册 query；`GET /health` 返回 `{"status": "ok", "agents_loaded": N, "redis_subscribed": true}`
- [ ] T023 [US2] 修改 `backend/src/runtime/loader.py`（若 T014 不完整则补充）：确保 Redis 订阅断连后在后台自动重试（指数退避，最大 60s），重试期间 RuntimeContext 数据继续可用

**Checkpoint**: 运行时 `uvicorn src.main_runtime:app` 独立启动，`/health` 正常，发布后 10s 内热加载

---

## Phase 5: US3 - 运行时池化管理避免重复加载（P1）

**目标**: AgentPool/ToolPool/SkillPool/MCPConnectionPool 生效，MCP 长连接复用，对话前置初始化 ≤ 50ms P95。

**独立测试**: 对同一 Agent 连续发起 10 次对话请求，验证 MCP 连接建立次数 ≤ 1（通过日志或 MCPConnectionPool.stats()）；Agent 初始化次数 = 1。

### US3 测试（TDD—先写测试，确认失败）

- [ ] T024 [P] [US3] 写 `backend/tests/unit/test_mcp_pool.py`：测试 MCPConnectionPool 单连接复用（连续调用 call_tool 只建立 1 次连接）；测试连接断开后自动重连；测试 asyncio.Lock 串行化（并发调用不混淆）（TDD：FAIL）
- [ ] T025 [P] [US3] 写 `backend/tests/unit/test_tool_pool.py`：测试 ToolPool.build_from_snapshot 构建 LangChain StructuredTool；测试 MCP 工具使用 MCPToolStrategy（TDD：FAIL）

### US3 实现

- [ ] T026 [US3] 重构 `backend/src/agents/single_agent.py` 为 `SingleAgentNode(BaseNode)`：`execute(context: AgentContext) -> AgentResult` 和 `stream(context: AgentContext) -> AsyncIterator[StreamEvent]`；工具列表从 `context.tool_pool.get_lc_tools(agent_entry.tool_ids)` 获取（不再每次重新构建）；MCP 调用通过 MCPToolStrategy + MCPConnectionPool（不再每次新建连接）；保留现有流式事件类型（answer/thinking/tool_start/tool_end/tool_error/__done__/__error__）；完整 Google docstring + 类型注解
- [ ] T027 [US3] 重构 `backend/src/agents/multi_agent.py` 为 `MultiAgentNode(BaseNode)`：`execute(context: AgentContext) -> AgentResult` 和 `stream(context: AgentContext) -> AsyncIterator[StreamEvent]`；路由逻辑调用 `route_multi_agent`；子 Agent 从 `context.agent_pool.get(sub_agent_id)` 获取；**修复单路由直传流式**（当 `route.is_single and route.confidence >= threshold` 时直接 `async for event in sub_agent_node.stream(context): yield event`）；多路由场景保持现有批量聚合（兼容已有行为）；完整 Google docstring + 类型注解
- [ ] T028 [US3] 重构 `backend/src/services/query_service.py`：移除 `db: AsyncSession` 参数（改为接收 `context: RuntimeContext`）；`execute_query(context, pipeline_uid, query, session_id)` 从 `context.pipeline_cache` 获取 pipeline、从 `context.agent_pool` 获取 agent，调用 `SingleAgentNode` 或 `MultiAgentNode`；`execute_stream_query` 同理；对话期间零数据库读取
- [ ] T029 [US3] 修改 `backend/src/api/v1/query.py`：移除 `db: AsyncSession = Depends(get_db)` 依赖，改为 `context: RuntimeContext = Depends(get_runtime_context)`（从 `main_runtime.py` 的 app.state 获取）；调整 `execute_query` / `execute_stream_query` 调用签名

**Checkpoint**: 连续 10 次对话请求，MCP 连接建立次数 ≤ 1；前置初始化时延 ≤ 50ms

---

## Phase 6: US4 - 多 Agent 单路由真实流式输出（P2）

**目标**: 多 Agent 流水线路由识别为单一子 Agent 时，SSE 事件流为 token 级流式（TTFT 与单 Agent 相差 ≤ 200ms）。

**独立测试**: 配置多 Agent 流水线，提交明确针对单子 Agent 的查询，通过 SSE 接口验证收到 `answer` token 级事件流，不是单次 `answer` 批量推送。

### US4 测试（TDD—先写测试，确认失败）

- [ ] T030 [P] [US4] 写 `backend/tests/integration/test_multi_agent_stream.py`：测试多 Agent 单路由场景 SSE 事件流包含多个 `answer` token 事件（而非单次批量）；测试后置检测在 `__done__` 前执行；测试 `tool_error` 事件实时推送（TDD：FAIL）

### US4 实现

- [ ] T031 [US4] 验证并补充 `MultiAgentNode.stream()` 中单路由直传逻辑（依赖 T027）：确认当 `route.is_single and confidence >= threshold` 时完整透传子 Agent 所有 `StreamEvent`，包括 `tool_start`/`tool_end`/`tool_error`；多路由场景聚合结果以单次 `answer` + `__done__` 事件推送
- [ ] T032 [US4] 修改 `backend/src/services/query_service.py` 中 `execute_stream_query` 的 `MULTI_AGENT` 分支：移除"退化为批量推送"逻辑，调用 `MultiAgentNode.stream(context)` 直接 yield 事件；后置检测从 `__done__` 事件的 `answer` 字段提取完整回答

**Checkpoint**: 多 Agent 单路由流式 TTFT P95 与单 Agent 相差 ≤ 200ms

---

## Phase 7: US5 - 基础节点设计模式与编码规范（P2）

**目标**: BaseNode/Strategy 抽象完整，所有公共 API 覆盖 Google docstring + 类型注解；新增工具协议无需修改主流程。

**独立测试**: 代码审查：公共方法 docstring 覆盖率 ≥ 95%，mypy 通过；添加新 `BaseToolStrategy` 子类只需注册，不修改 SingleAgentNode 主逻辑。

### US5 实现

- [ ] T033 [P] [US5] 补充 `backend/src/agents/intent_router.py` 缺失的 Google docstring 和类型注解（`IntentResult`/`RouteResult`/`route_intent`/`route_multi_agent` 公共方法）
- [ ] T034 [P] [US5] 补充 `backend/src/agents/detection.py` 缺失的 Google docstring 和类型注解（`run_pre_detection`/`run_post_detection`）
- [ ] T035 [P] [US5] 补充 `backend/src/runtime/context.py`、`backend/src/runtime/loader.py` 所有公共方法的 Google docstring
- [ ] T036 [US5] 验证工厂注册机制：在 `backend/src/agents/strategies/__init__.py` 中实现 `StrategyFactory`（`{protocol: strategy_class}` 注册表），SingleAgentNode/MultiAgentNode 通过 `StrategyFactory.get(protocol)` 获取策略，不再有 `if protocol == MCP` 分支

**Checkpoint**: mypy 通过；ruff format + ruff check 通过；添加新策略类不修改 SingleAgentNode 主逻辑

---

## Phase 8: US3-P2 - Agent 池淘汰策略（P2 可选）

**目标**: AgentPool 支持最大容量配置，超限时按评分淘汰，淘汰事件记录结构化日志（FR-018）。

**独立测试**: 配置 `RUNTIME_AGENT_POOL_MAX_SIZE=3`，加载 4 个 Agent，验证最老且空闲最久的被淘汰，日志中有 `agent_pool.evict` 记录。

### US3-P2 测试（TDD）

- [ ] T037 [P] [US3] 写 `backend/tests/unit/test_agent_pool_eviction.py`：测试池满时 evict_one 触发；测试评分公式（老 + 空闲 → 高分）；测试淘汰后 pool 容量恢复（TDD：FAIL）

### US3-P2 实现

- [ ] T038 [US3] 确认 `AgentPool`（依赖 T012）中 `RUNTIME_AGENT_POOL_MAX_SIZE` 配置生效（0 = 不限制）；验证 `evict_one` 评分逻辑和 `on_eviction` 结构化日志字段（agent_id/version/score）完整

**Checkpoint**: 池满时自动淘汰，日志可观测

---

## Phase 9: Polish & 质量门禁

**目标**: 全量测试通过，质量门禁满足，更新依赖声明和启动文档。

- [ ] T039 [P] 执行 `uv run pytest --cov=src --cov-report=term-missing`，确认覆盖率 ≥ 80%，新增文件关键路径 ≥ 95%
- [ ] T040 [P] 执行 `uv run ruff format . && uv run ruff check .`，修复所有 lint 问题
- [ ] T041 [P] 执行 `uv run mypy src/`，确认 `disallow_untyped_defs = true` 全部通过
- [ ] T042 [P] 执行 `uv sync` 确认 `redis[asyncio]` 已正确写入 `backend/uv.lock`
- [ ] T043 更新 `backend/.env.example`：补充 `REDIS_URL`、`REDIS_STREAM_KEY`、`RUNTIME_AGENT_LOAD_MODE`、`RUNTIME_AGENT_POOL_MAX_SIZE` 四个新环境变量及说明注释
- [ ] T044 [P] 写 `backend/tests/contract/test_query_contract.py`（契约回归）：验证 `POST /api/v1/query` 请求/响应 JSON Schema 与改造前完全一致（`code`/`message`/`data.answer`/`data.tools_called`/`data.session_id`/`data.latency_ms` 字段不变）
- [ ] T045 [P] 写 `backend/tests/integration/test_runtime_no_db.py`：验证对话期间零数据库调用（mock DB session，断开后 query 仍正常响应，不抛出 DB 相关异常）

**Checkpoint**: 所有质量门禁通过，可合并 PR

---

## 依赖与执行顺序

### Phase 依赖关系

- **Phase 1（Setup）**: 无依赖，可立即开始
- **Phase 2（Foundational）**: 依赖 Phase 1 完成；**阻塞 Phase 3/4/5/6/7/8**
- **Phase 3（US1）**: 依赖 Phase 2；不依赖 Phase 4/5/6（可并行）
- **Phase 4（US2）**: 依赖 Phase 2 + T007/T013/T014；不依赖 Phase 3
- **Phase 5（US3）**: 依赖 Phase 2（T007-T014 全部完成）；**T026/T027 是 Phase 6 的前置**
- **Phase 6（US4）**: 依赖 T027/T028/T029（Phase 5）
- **Phase 7（US5）**: 依赖 Phase 5 基本完成（T026/T027）；可与 Phase 6 并行
- **Phase 8（US3-P2）**: 依赖 T012；可与 Phase 6/7 并行
- **Phase 9（Polish）**: 依赖所有必选 Phase 完成

### 用户故事间依赖

- **US1（P1）**: Phase 2 完成后可独立开始
- **US2（P1）**: Phase 2 完成后可独立开始（与 US1 并行）
- **US3（P1）**: Phase 2 完成后可独立开始（依赖 T026/T027 供 US4 使用）
- **US4（P2）**: 依赖 US3 中 T027/T028/T029
- **US5（P2）**: 依赖 US3 主体完成
- **US3-P2（P2）**: 依赖 T012，可与 US4/US5 并行

### Phase 内任务顺序

```
Phase 1:  T001 → T002 [P] + T003 [P] → T004 → T005 → T006
Phase 2:  T007 → T008 [P] + T009 [P] + T010 [P] + T011 [P] → T012 → T013 → T014
Phase 3:  T015 [P] + T016 [P] (TDD) → T017 → T018 → T019
Phase 4:  T020 [P] + T021 [P] (TDD) → T022 → T023
Phase 5:  T024 [P] + T025 [P] (TDD) → T026 → T027 → T028 → T029
Phase 6:  T030 (TDD) → T031 → T032
Phase 7:  T033 [P] + T034 [P] + T035 [P] → T036
Phase 8:  T037 (TDD) → T038
Phase 9:  T039 [P] + T040 [P] + T041 [P] + T042 [P] → T043 → T044 [P] + T045 [P]
```

---

## 并行执行示例

### Phase 2（Foundational）并行组

```
同时启动（不同文件，无依赖）:
  T008: backend/src/agents/pool/mcp_pool.py
  T009: backend/src/agents/strategies/
  T010: backend/src/agents/pool/tool_pool.py
  T011: backend/src/agents/pool/skill_pool.py
等待以上完成后:
  T012: backend/src/agents/pool/agent_pool.py
  T013: backend/src/runtime/context.py
  T014: backend/src/runtime/loader.py
```

### Phase 5（US3）并行组

```
同时启动（TDD）:
  T024: tests/unit/test_mcp_pool.py
  T025: tests/unit/test_tool_pool.py
等待以上失败确认后，同时实现:
  T026: agents/single_agent.py → SingleAgentNode
  T027: agents/multi_agent.py  → MultiAgentNode（包含流式修复）
等待完成后顺序执行:
  T028: services/query_service.py（重构）
  T029: api/v1/query.py（适配新签名）
```

---

## 实现策略

### MVP 范围（仅 P1 用户故事）

1. 完成 Phase 1（Setup）
2. 完成 Phase 2（Foundational）→ **关键：阻塞所有后续**
3. 完成 Phase 3（US1：管理端发布）
4. 完成 Phase 4（US2：运行时热加载）
5. 完成 Phase 5（US3：池化零 DB 读取）
6. **STOP & VALIDATE**：三个 P1 用户故事独立测试通过
7. 运行时 `uvicorn src.main_runtime:app` 独立部署验证

### 增量交付

1. Phase 1 + Phase 2 → 基础设施就绪
2. Phase 3 → 管理端发布能力（前端可接入）
3. Phase 4 + Phase 5 → 运行时池化（性能提升可见）
4. Phase 6 → 多 Agent 流式修复（用户体验提升）
5. Phase 7 + Phase 8 → 代码质量 + 资源管理
6. Phase 9 → 质量门禁，合并主干

---

## 注意事项

- `[P]` 任务可并行，不同文件，无未完成依赖
- `[US#]` 标签追踪任务到对应用户故事
- TDD 任务：先写测试确认 FAIL，再实现功能
- 每个 Phase 完成后执行 Checkpoint 验证，再进入下一 Phase
- `main.py` 保留向后兼容（等同管理端），不删除
- **严禁对话请求期间读取数据库**：Phase 5 完成后用 `test_runtime_no_db.py` 强制验证
