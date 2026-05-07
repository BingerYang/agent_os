# 实现计划：Backend 管理端/运行时拆分与 Agent 编排池化重构

**分支**: `003-backend-split-runtime` | **日期**: 2026-05-06 | **规格**: [spec.md](./spec.md)  
**输入**: 功能规格来自 `specs/003-backend-split-runtime/spec.md`

---

## 摘要

本次重构将 `backend` 拆分为可独立部署的**管理端**（CRUD + Agent 发布）和**运行时**（对话接口）两个 FastAPI 应用。核心变更：

1. 通过 Redis Stream 实现 Agent 配置的异步热加载，替换现有 SSE 内存事件总线
2. 引入 AgentPool / ToolPool / SkillPool / MCPConnectionPool 池化管理，消除对话中的重复初始化
3. 以 `BaseNode` + 策略模式重构 `agents/` 目录，职责清晰，支持 MCP/HTTP/BUILTIN 三种工具协议
4. 修复多 Agent 流水线单路由场景的流式退化问题（当前退化为批量推送）
5. 补充完整 Google 风格 docstring 和类型注解

**不变**：所有现有管理端 CRUD API 接口契约（无破坏性变更）；`POST /api/v1/query` 接口契约不变（仅实现重构）。

---

## 技术上下文

**语言/版本**: Python 3.12  
**主要依赖**: FastAPI ≥ 0.115.0、deepagents ≥ 0.1.0、langchain ≥ 1.0.0、langgraph ≥ 1.0.0、redis[asyncio]（新增）、mcp ≥ 1.27.0、sqlalchemy[asyncio] ≥ 2.0.0  
**数据库**: SQLite（开发）/ MySQL 8.0+（生产），通过 `DATABASE_URL` 切换  
**测试**: pytest + pytest-asyncio（`asyncio_mode = "auto"`）  
**目标平台**: Linux 服务器（容器化）  
**项目类型**: Web 服务（双 FastAPI 应用）  
**性能目标**: 池化后对话前置初始化 ≤ 50ms P95；Redis 热加载延迟 ≤ 10s P99  
**约束**: 对话期间零数据库读取；MCP 单连接串行化；Agent 池超限时按评分淘汰  
**规模**: 支持 ≤ 100 个已发布 Agent 常驻内存（V1 默认无上限，可配置）

---

## Constitution Check

*Gate: Phase 0 研究前 MUST 通过检查；Phase 1 设计后重新确认。*

| 原则 | 状态 | 说明 |
|------|------|------|
| I. RESTful 规范 | ✅ 合规 | 新增 `PATCH /agents/{id}/publish` 符合 RESTful；所有响应使用 `ApiResponse[T]` |
| II. 技术栈合规 | ⚠️ 预存偏差 | Python 3.12 ✅、FastAPI ✅、langchain ≥ 1.0.0 ✅、deepagents ✅；**SQLite 开发模式**和**React 前端**为 001 期已建立的偏差，本期不引入新偏差；**redis[asyncio]** 为新增依赖（见 Complexity Tracking） |
| III. 中文文档 | ✅ 合规 | 所有规格/计划文档使用中文；代码业务注释使用中文 |
| IV. TDD | ✅ 合规 | 每个用户故事先写测试（MUST FAIL），再实现 |
| V. YAGNI | ✅ 合规（含必要复杂度） | 详见 Complexity Tracking；所有引入的抽象均有明确需求驱动 |

---

## 项目结构

### 规格文档（本功能）

```text
specs/003-backend-split-runtime/
├── plan.md              # 本文件
├── research.md          # Phase 0 研究
├── data-model.md        # Phase 1 数据模型
├── contracts/api.md     # Phase 1 接口契约
├── quickstart.md        # Phase 1 快速启动
├── checklists/          # 规格质量检查
└── tasks.md             # Phase 2 任务清单（由 /speckit-tasks 生成）
```

### 源码结构（变更部分）

```text
backend/src/
├── main.py                        # 保留（向后兼容 = 管理端）
├── main_management.py             # [NEW] 管理端入口
├── main_runtime.py                # [NEW] 运行时入口
│
├── api/v1/
│   ├── router.py                  # [MODIFIED] 管理端路由（移除 query）
│   ├── agents.py                  # [MODIFIED] + PATCH /{id}/publish 端点
│   ├── query.py                   # [MODIFIED] 实现改用 RuntimeContext 池
│   └── ...                        # 其余 CRUD 路由不变
│
├── agents/
│   ├── __init__.py
│   ├── base.py                    # [NEW] BaseNode ABC, AgentContext, AgentResult, StreamEvent
│   ├── detection.py               # [REFACTORED] 接受 DetectionRule 列表而非 ORM 查询
│   ├── intent_router.py           # [REFACTORED] 返回类型规范化
│   ├── single_agent.py            # [REFACTORED] → SingleAgentNode(BaseNode)
│   ├── multi_agent.py             # [REFACTORED] → MultiAgentNode(BaseNode) + 流式修复
│   ├── pool/
│   │   ├── __init__.py
│   │   ├── agent_pool.py          # [NEW] AgentPool (含淘汰策略, P2)
│   │   ├── tool_pool.py           # [NEW] ToolPool
│   │   ├── skill_pool.py          # [NEW] SkillPool
│   │   └── mcp_pool.py            # [NEW] MCPConnectionPool (单连接 + Lock)
│   └── strategies/
│       ├── __init__.py
│       ├── base.py                # [NEW] BaseToolStrategy ABC
│       ├── mcp_strategy.py        # [NEW] MCP 协议策略（迁移自 single_agent.py）
│       └── http_strategy.py       # [NEW] HTTP 协议策略（迁移自 single_agent.py）
│
├── runtime/
│   ├── __init__.py
│   ├── context.py                 # [NEW] RuntimeContext 单例（持有所有池）
│   └── loader.py                  # [NEW] DB 全量加载 + Redis Stream 订阅
│
├── models/
│   └── agent_publish.py           # [NEW] AgentPublish ORM 模型
│
└── services/
    ├── query_service.py           # [REFACTORED] 改用 RuntimeContext，不读 DB
    └── publish_service.py         # [NEW] 发布 Agent + Redis Stream 推送
```

**结构决策**: 采用单 `src/` 包 + 双入口文件模式，最小化结构变动，符合 YAGNI 原则。

---

## Complexity Tracking

| 违反项 | 必要性 | 排除更简单方案的原因 |
|--------|--------|---------------------|
| 双 FastAPI 应用入口 | 显式独立部署需求（FR-001/FR-005）| 单应用无法实现运行时与管理端进程级隔离 |
| 引入 `redis[asyncio]` 依赖（不在 Constitution II 中）| FR-003/FR-008 要求跨进程异步通知 | SSE 内存事件总线仅支持同进程，分离部署后失效 |
| BaseNode + 策略模式 | FR-013/FR-014；MCP/HTTP/BUILTIN 三种协议实现满足"三处重复代码方可提取"规则 | 直接 `if protocol == MCP` 会在节点主流程中积累分支，新协议无法不修改主逻辑地添加 |
| MCPConnectionPool + asyncio.Lock | FR-011；重复 MCP 连接是当前 P95 性能瓶颈 | 每次调用新建连接：TCP 握手 + MCP 初始化开销 > 200ms |
| AgentPoolEntry 含淘汰评分字段（P2） | FR-018；资源上限可配 | 无淘汰机制则池无上限，高并发发布场景内存持续增长 |

---

## 实现分阶段计划

### Phase 1：数据库 & 新 ORM 模型（基础）

**目标**: 为发布功能准备 DB 层，不影响现有功能。

**任务**:
1. 新增 `AgentPublish` ORM 模型（`backend/src/models/agent_publish.py`）
2. 修改 `Agent` ORM 模型，新增 `published_version`、`last_published_at` 字段
3. 生成 Alembic 迁移脚本
4. 更新 `models/__init__.py` 导出

**验收**: `alembic upgrade head` 成功；`AgentPublish` 表存在。

---

### Phase 2：管理端发布服务 & API

**目标**: 运营人员可通过 API 发布 Agent，写库 + Redis Stream 推送。

**任务**:
1. 新增 `publish_service.py`：
   - `publish_agent(db, agent_id) → PublishResult`：创建快照、写 `AgentPublish`、更新 `agents.published_version`、推 Redis Stream
   - Redis 推送失败不回滚（返回 `redis_notified=false`）
2. 修改 `agents.py`：新增 `PATCH /{id}/publish` 端点
3. 修改 `agents.py`：新增 `GET /{id}/publishes` 端点
4. 写测试：`tests/integration/test_publish_agent.py`

**验收**: 发布请求返回 `publish_id`、Redis Stream 有事件、`AgentPublish` 表有记录。

---

### Phase 3：运行时核心组件（池 + 加载器）

**目标**: 构建运行时内存池和启动加载机制。

**任务**:
1. 实现 `agents/pool/mcp_pool.py`（MCPConnectionPool + asyncio.Lock 串行化 + 自动重连）
2. 实现 `agents/pool/tool_pool.py`（ToolPool，从 `AgentPublish.config_snapshot` 构建 StructuredTool）
3. 实现 `agents/pool/skill_pool.py`（SkillPool）
4. 实现 `agents/pool/agent_pool.py`（AgentPool，含淘汰评分 P2 + 告警预留接口）
5. 实现 `runtime/context.py`（RuntimeContext 单例）
6. 实现 `runtime/loader.py`：
   - `load_from_db(db)` → 全量加载（fail fast 若 DB 不可用）
   - `start_redis_subscriber(context, redis_url)` → XREAD 从 `$` 开始，后台任务
   - 事件处理：de-duplicate by agent_id → max publish_id，fetch snapshot from DB，update pools
7. 写测试：`tests/unit/test_agent_pool.py`、`tests/unit/test_mcp_pool.py`、`tests/integration/test_loader.py`

**验收**: 运行时启动加载 5 个已发布 Agent；10 秒内感知 Redis 事件并更新池；MCP 工具调用复用连接。

---

### Phase 4：Agent 节点抽象重构

**目标**: 以 `BaseNode` 重构 `single_agent.py` / `multi_agent.py`，提取工具策略类。

**任务**:
1. 实现 `agents/base.py`（`BaseNode` ABC、`AgentContext`、`AgentResult`、`StreamEvent`）
2. 实现 `agents/strategies/base.py`（`BaseToolStrategy` ABC）
3. 实现 `agents/strategies/mcp_strategy.py`（从 `single_agent.py` 提取 MCP 调用逻辑，使用 MCPConnectionPool）
4. 实现 `agents/strategies/http_strategy.py`（从 `single_agent.py` 提取 HTTP 调用逻辑）
5. 重构 `agents/single_agent.py` → `SingleAgentNode(BaseNode)`:
   - `execute(context) → AgentResult`
   - `stream(context) → AsyncIterator[StreamEvent]`
   - 工具构建从 ToolPool 获取，不重新连接 MCP
6. 重构 `agents/multi_agent.py` → `MultiAgentNode(BaseNode)`:
   - `execute(context) → AgentResult`
   - `stream(context) → AsyncIterator[StreamEvent]`：**修复单路由直传流式**（当 `route.is_single and confidence >= threshold` 时直接 `yield` 子 Agent 的 stream 事件）
7. 所有公共方法补充 Google 风格 docstring + 完整类型注解
8. 写测试：`tests/unit/test_single_agent_node.py`、`tests/unit/test_multi_agent_node.py`、`tests/integration/test_multi_agent_stream.py`（验证单路由直传流式）

**验收**: 单 Agent 流式事件序列正确；多 Agent 单路由流式 TTFT 与单 Agent 相差 ≤ 200ms；所有 docstring 覆盖率 ≥ 95%。

---

### Phase 5：双入口 & query_service 重构

**目标**: 创建双应用入口，重构 `query_service.py` 使用 RuntimeContext。

**任务**:
1. 新增 `main_management.py`（管理端 FastAPI 应用，包含全部 CRUD 路由，不含 query）
2. 新增 `main_runtime.py`（运行时 FastAPI 应用，仅含 query 路由；lifespan 启动时调用 `loader.load_from_db` 和 `loader.start_redis_subscriber`）
3. 重构 `services/query_service.py`：
   - 从函数签名中移除 `db: AsyncSession` 参数（对话中不读 DB）
   - 改从 `RuntimeContext` 获取 pipeline 配置、agent 实例
   - 调用 `MultiAgentNode.stream()` 替代旧的批量退化逻辑
4. 修改 `api/v1/router.py`：提取为 `management_router`（当前路由集合）
5. 修改 `api/v1/query.py`：适配新的无 `db` 签名的 `execute_query` / `execute_stream_query`
6. 验证 `main.py`（向后兼容模式）仍然可启动
7. 写测试：`tests/integration/test_runtime_no_db.py`（对话中无 DB 调用验证）、`tests/contract/test_query_contract.py`（接口契约不变）

**验收**: 管理端 / 运行时可独立启动；对话接口无 DB 读取（mock DB 后 query 仍正常响应）；所有现有接口契约测试通过。

---

### Phase 6：端到端验证 & 文档

**目标**: 全量 TDD 通过，代码质量门禁通过。

**任务**:
1. 运行完整测试套件，确认覆盖率 ≥ 80%
2. `ruff format . && ruff check .` 全部通过
3. `mypy src/` 通过（`disallow_untyped_defs = true`）
4. 验证 SC-001：池化后前置初始化 ≤ 50ms（基准测试）
5. 验证 SC-003：MCP 连接复用（1 小时内 100 次调用，连接建立次数 ≤ 5）
6. 验证 SC-004：多 Agent 单路由流式 TTFT 差异 ≤ 200ms
7. 更新 `backend/pyproject.toml`，新增 `redis[asyncio]` 依赖

**验收**: 所有 6 个阶段的测试全部通过；质量门禁 7 项全部满足。

---

## Codex 执行命令

| Phase | 文件 | 指令 |
|-------|------|------|
| P1 | `backend/src/models/agent_publish.py` | 创建 AgentPublish ORM 模型（含 id/agent_id/version/config_snapshot/is_active/published_at/published_by/created_at/updated_at 字段，参照 data-model.md） |
| P1 | `backend/src/models/agent.py` | 新增 published_version（INT NULL）和 last_published_at（DATETIME NULL）字段 |
| P1 | Alembic | 生成迁移脚本 `alembic revision --autogenerate -m "add_agent_publish_table"` |
| P2 | `backend/src/services/publish_service.py` | 实现 publish_agent 函数（序列化快照、写 AgentPublish、Redis Stream XADD） |
| P2 | `backend/src/api/v1/agents.py` | 新增 PATCH /{id}/publish 和 GET /{id}/publishes 端点 |
| P3 | `backend/src/agents/pool/mcp_pool.py` | 实现 MCPConnectionPool（单连接 + asyncio.Lock + 自动重连） |
| P3 | `backend/src/agents/pool/tool_pool.py` | 实现 ToolPool（从 config_snapshot 构建 StructuredTool） |
| P3 | `backend/src/agents/pool/agent_pool.py` | 实现 AgentPool（含淘汰评分 0.3×age + 0.7×idle） |
| P3 | `backend/src/runtime/loader.py` | 实现 load_from_db（fail fast）+ start_redis_subscriber（XREAD from $） |
| P4 | `backend/src/agents/base.py` | 实现 BaseNode ABC、AgentContext、AgentResult、StreamEvent |
| P4 | `backend/src/agents/strategies/` | 实现 BaseToolStrategy、MCPToolStrategy、HTTPToolStrategy |
| P4 | `backend/src/agents/single_agent.py` | 重构为 SingleAgentNode(BaseNode)，工具从 ToolPool/MCPPool 获取 |
| P4 | `backend/src/agents/multi_agent.py` | 重构为 MultiAgentNode(BaseNode)，修复单路由流式直传 |
| P5 | `backend/src/main_management.py` | 创建管理端 FastAPI 应用（不含 query 路由） |
| P5 | `backend/src/main_runtime.py` | 创建运行时 FastAPI 应用（仅含 query；lifespan 调用 loader） |
| P5 | `backend/src/services/query_service.py` | 重构：移除 db 参数，改从 RuntimeContext 获取数据 |
