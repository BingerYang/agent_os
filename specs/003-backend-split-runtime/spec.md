# 功能规格说明书：Backend 管理端/运行时拆分与 Agent 编排池化重构

**功能分支**: `003-backend-split-runtime`  
**创建日期**: 2026-05-06  
**状态**: 草稿  
**输入**: 用户描述："把 backend 分为管理端和运行时且可分开部署；通过 Redis Stream 同步发布信号；运行时池化管理 Tool/Skill/Agent，保持 MCP Server 长连接；多 Agent 单路由场景支持真实流式；使用设计模式使代码可维护；完整类型注解与 Google docstring。"

## 技术规范（延续自第一期项目决策）

> 本节记录第一期（001-agent-dispatch-platform）已确定的技术选型，在本次重构中须严格遵守，不重新评估。

### 语言与运行时

- **Python 3.12**（`requires-python = ">=3.12"`）
- 包管理：**uv**；依赖声明在 `backend/pyproject.toml`

### 后端框架

| 组件 | 版本约束 | 用途 |
|------|---------|------|
| FastAPI | ≥ 0.115.0 | HTTP API 框架 |
| Uvicorn (standard) | ≥ 0.30.0 | ASGI 服务器 |
| Pydantic v2 | ≥ 2.0.0 | 数据校验与序列化 |
| pydantic-settings | ≥ 2.0.0 | 环境变量管理（`Settings` 类） |
| sse-starlette | ≥ 2.1.0 | SSE 流式响应（`EventSourceResponse`） |

### Agent 框架（禁止使用已废弃 API）

| 组件 | 版本约束 | 用途 |
|------|---------|------|
| deepagents | ≥ 0.1.0 | 主 Agent 执行引擎（`create_deep_agent`） |
| langchain | ≥ 1.0.0 | 标准 Agent API（`create_agent`）、Middleware 体系 |
| langgraph | ≥ 1.0.0 | 多 Agent 编排底层（`StateGraph`） |
| langchain-openai | ≥ 0.2.0 | LLM 接入（`ChatOpenAI`） |
| langchain-community | ≥ 0.3.0 | 社区工具扩展 |

**禁止使用**（第一期已废弃，本次重构不得引入）：
- `AgentExecutor`
- `create_react_agent`（`langgraph.prebuilt`）
- LCEL 管道语法（`prompt | llm | parser`）
- `langgraph.prebuilt` 模块的任何导入

### MCP 协议

- **mcp** ≥ 1.27.0；使用 `ClientSession` + `streamable_http_client` 与 MCP Server 通信
- 工具 inputSchema 通过 `session.list_tools()` 动态获取，构建 Pydantic 参数模型

### 数据库

| 组件 | 用途 |
|------|------|
| SQLAlchemy 2.x async ORM | 数据访问层（`AsyncSession`） |
| Alembic | Schema 迁移管理 |
| aiosqlite ≥ 0.20.0 | 开发环境（`sqlite+aiosqlite://`） |
| aiomysql ≥ 0.2.0 | 生产环境（`mysql+aiomysql://`） |

切换方式：`DATABASE_URL` 环境变量；代码零修改。

### 新增依赖（本次重构引入）

- **redis-py async**（`redis[asyncio]`）：Redis Stream 生产与消费，替代现有 SSE 内存事件总线

### HTTP 客户端与加密

- **httpx** ≥ 0.27.0：工具 HTTP 调用、MCP 连接
- **cryptography** ≥ 42.0.0：API Key AES-256-GCM 加解密

### 测试与代码质量

| 工具 | 版本约束 | 用途 |
|------|---------|------|
| pytest | ≥ 8.0.0 | 测试运行器（`asyncio_mode = "auto"`） |
| pytest-asyncio | ≥ 0.23.0 | async 测试支持 |
| pytest-cov | ≥ 5.0.0 | 覆盖率报告 |
| ruff | ≥ 0.6.0 | Lint + Format（行长 120，target py312） |
| mypy | ≥ 1.10.0 | 静态类型检查（`disallow_untyped_defs = true`） |

### 前端

- **React + TypeScript + Vite**（已于第一期末从 Vue 迁移）
- API 响应统一使用泛型 `ApiResponse[T]`（`code`、`message`、`data`、`timestamp`）

### 统一响应规范

```
ApiResponse[T]:
  code: int        # 0=成功，非0=错误
  message: str
  data: T
  timestamp: datetime
```

---

## 用户故事与测试场景

### 用户故事 1 - 管理端独立部署并通过 Redis Stream 发布 Agent 变更（优先级：P1）

运营人员在管理端"Agent 管理"页面完成 Agent 配置后，点击"发布"按钮；系统将该发布记录写入数据库并向 Redis Stream 发送发布信号。此后，管理端可完全独立运行，无需与运行时进程共享内存或进程空间。

**为何此优先级**：这是两端解耦的核心触发点。管理端能独立部署，是运行时可弹性扩容的前提。

**独立测试**：仅启动管理端服务（不启动运行时），完成 Agent 发布操作，验证数据库中出现发布记录、Redis Stream 中出现对应事件，且全程不依赖运行时进程。

**验收场景**：

1. **Given** 运营人员配置并保存了一个 Agent，**When** 点击"发布"，**Then** 系统将 Agent 状态更新为已发布并写入数据库，同时向 Redis Stream（频道 `agent.publish`）推送包含 `publish_id`、`agent_id`、`version`、`timestamp` 的事件，操作端到端完成时间不超过 2 秒。
2. **Given** Redis 暂时不可用，**When** 运营人员执行发布操作，**Then** 系统仍成功写库并给出明确错误提示（Redis 推送失败），数据库状态不回滚，运营人员可重试发布通知。
3. **Given** 管理端与运行时分开部署在不同主机，**When** 管理端完成任意 CRUD 操作，**Then** 管理端 API 正常响应，不因运行时不可用而失败。

---

### 用户故事 2 - 运行时订阅 Redis Stream 并热加载已发布的 Agent（优先级：P1）

运行时服务启动时从数据库加载最新的已发布 Agent 配置（可选一次性加载或按需延迟加载），并持续订阅 Redis Stream；每当管理端发布新 Agent 或更新，运行时自动获取最新配置，无需重启。

**为何此优先级**：运行时无需重启即可感知配置变更，是平台可用性和动态扩展的核心保障。

**独立测试**：启动运行时服务后，在管理端发布一个新 Agent；在 10 秒内对该 Agent 发起对话请求，验证运行时已用最新配置响应，无需重启。

**验收场景**：

1. **Given** 运行时首次启动，**When** 初始化完成，**Then** 运行时已将数据库中所有已发布 Agent 的配置加载到内存（或注册为懒加载条目），并开始订阅 Redis Stream，启动总时延不超过 10 秒（含数据库加载）。
2. **Given** 管理端向 Redis Stream 发布新 Agent 事件，**When** 运行时消费到该事件，**Then** 运行时在 10 秒内将对应 Agent 配置加载/更新到 Agent 池，后续对话请求可立即使用新配置。
3. **Given** 运行时已缓存某 Agent，**When** 管理端发布该 Agent 的更新版本，**Then** 运行时使旧缓存失效，加载新版本配置，正在进行的对话使用旧版本完成，新对话使用新版本。
4. **Given** Redis Stream 连接中断，**When** 运行时检测到断连，**Then** 运行时继续用最后一次成功加载的配置服务对话，并在后台尝试重新订阅，不崩溃、不中断现有对话。

---

### 用户故事 3 - 运行时通过 Agent/Tool/Skill/MCP 池化管理避免重复加载（优先级：P1）

运行时在整个生命周期内，为每个已发布的 Agent 维护初始化后的实例池；Tool 和 Skill 的描述信息及执行配置同样池化管理；MCP Server 保持长连接，避免每次对话重新握手。同一 Agent 实例在并发请求中被复用（无状态部分），从而消除每次对话的重复初始化开销。

**为何此优先级**：频繁初始化 LangChain Agent、重建 MCP 连接是当前性能瓶颈，池化是运行时实用性的前提。

**独立测试**：对同一 Agent 连续发起 10 次对话请求，监控 MCP Server 连接建立次数（应为 1 次或维持长连接），以及 Agent 初始化次数（应为 1 次），验证池化生效。

**验收场景**：

1. **Given** 运行时已加载某 Agent，**When** 收到针对该 Agent 的对话请求，**Then** 直接从 Agent 池取出对应实例执行，不重新创建 LangChain Agent 对象，对话前置时延相比每次新建减少 80% 以上。
2. **Given** 某 MCP Server 已注册长连接，**When** 该 Agent 的工具需要调用 MCP，**Then** 复用已有连接执行工具调用，不重新建立 TCP/HTTP 连接（在连接健康的情况下）。
3. **Given** MCP Server 长连接断开，**When** 工具调用触发连接检测，**Then** 系统自动重连并完成工具调用，对上层调用方透明，不因连接断开返回错误。
4. **Given** 某 Agent 配置被更新（热加载），**When** 运行时刷新该 Agent，**Then** 旧的 Agent 实例（及对应的 MCP 长连接）被优雅关闭，新实例建立新连接；已在途的对话用旧实例完成。

---

### 用户故事 4 - 多 Agent 场景中智能路由识别为单 Agent 时支持真实流式输出（优先级：P2）

在多 Agent 编排模式下，当智能路由以高置信度判断仅需一个子 Agent 即可处理用户请求时，运行时直接将请求转发至该子 Agent 并以流式方式返回 token 级响应，不经过批量聚合步骤。

**为何此优先级**：当前多 Agent 流式响应退化为批量推送，用户体验差；单路由识别后流式直传是高频优化路径。

**独立测试**：配置一个多 Agent 流水线，提交一个明确针对单个子 Agent 的查询（使路由以高置信度选中唯一子 Agent），通过 SSE 接口验证响应为 token 级流式，第一个 token 到达时间与单 Agent 模式一致。

**验收场景**：

1. **Given** 多 Agent 流水线，**When** 路由结果为单一子 Agent 且置信度 ≥ 配置阈值，**Then** 运行时绕过聚合节点，直接对该子 Agent 执行流式调用，SSE 事件流包含 `answer`（token 级）、`tool_start`、`tool_end`、`__done__` 等标准事件。
2. **Given** 多 Agent 流水线，**When** 路由结果为多个子 Agent，**Then** 运行时按现有逻辑串行调用各子 Agent 并聚合，流式通道以单次 `answer` 事件推送最终聚合结果（现有行为保持兼容）。
3. **Given** 单路由直传场景，**When** 子 Agent 工具调用出现错误，**Then** 错误事件通过 SSE 通道实时推送（`tool_error` 事件），不丢失；后置检测在 `__done__` 事件发出前执行。

---

### 用户故事 5 - 基础节点以设计模式定义，职责清晰可维护（优先级：P2）

运行时的 Agent、Tool、Skill、工作流等交互节点以类实现，对外暴露统一接口；通过策略模式（执行方式可替换）、工厂模式（节点创建）、池模式（实例复用）等设计模式组织代码，使得添加新节点类型或替换执行策略不需要修改核心调度逻辑。

**为何此优先级**：无清晰抽象则新增节点类型（如工作流节点）会持续增加维护成本；设计模式确保扩展性。

**独立测试**：通过添加一个新的 Skill 执行策略（如"并行执行所有工具"），验证只需新增一个策略类并在配置中指定，无需修改现有 Agent 调度主流程代码。

**验收场景**：

1. **Given** 需要新增一种工具执行协议，**When** 开发者实现对应的执行策略类，**Then** 该策略可通过配置注册到工具执行器，无需修改现有 `single_agent.py` 或 `multi_agent.py` 中的分支逻辑。
2. **Given** 代码库中所有公共 API（节点类的公共方法、池管理器接口），**When** 开发者查阅，**Then** 每个公共方法均有完整 Google 风格 docstring，包含参数、返回值、可能抛出的异常说明。
3. **Given** 任意节点类，**When** 进行代码审查，**Then** 所有方法参数和返回值均有完整类型注解，无裸 `Any` 注解（除确实动态的场景外需加注释说明原因）。

---

### 边界情况

以下边界情况已确认决策，不再是开放问题：

- **DB 不可用时启动**：运行时启动时若无法连接数据库加载 Agent 配置，服务启动失败（fast-fail），不降级。运营人员需确保数据库可用后再启动运行时。
- **Agent 池资源淘汰**（P2）：当 Agent 池达到配置上限时，按"加载时间 × 空闲时长"加权评分淘汰得分最低的条目（即：很早加载且长期未访问的 Agent 优先淘汰）。淘汰事件记录结构化日志，为未来告警通知预留扩展点，但 V1 不实现告警通知。
- **MCP Server 连接模型**：V1 每个 MCP Server 维护单条长连接，调用时通过 `asyncio.Lock` 串行化并发请求，避免连接竞争。多连接池为 V2 优化项，接口设计需预留扩展点。
- **Redis Stream 重启消费策略**：运行时重启时，Redis Stream 消费从最新 ID（`$`）开始，忽略积压的历史事件（重启后通过数据库全量加载保证数据完整性）。正常运行期间，若同一 Agent 有多条积压事件，只处理 `publish_id` 最大的一条，其余丢弃。
- **时钟偏差**：分开部署时不处理管理端与运行时之间的时钟偏差问题，V1 阶段不需要跨节点时序保证。

## 功能需求

### 功能性需求

**管理端**

- **FR-001**: 管理端服务 MUST 作为独立可部署的 FastAPI 应用运行，不依赖运行时服务进程。
- **FR-002**: 管理端 MUST 提供"发布 Agent"操作接口；发布时 MUST 将发布记录（`publish_id`、`agent_id`、`version`、发布时间）写入数据库。
- **FR-003**: 管理端在写库成功后 MUST 向 Redis Stream（键名 `agent.publish`）推送发布事件；推送失败 MUST 返回明确错误，不影响数据库状态。
- **FR-004**: 管理端 MUST 继续提供全部现有 CRUD API（Agent、Tool、Skill、MCP Server、Pipeline、检测规则等），这些接口仅与数据库交互，不调用运行时。

**运行时**

- **FR-005**: 运行时服务 MUST 作为独立可部署的 FastAPI 应用运行，对话期间 MUST 不读取数据库（仅使用内存池中的数据）。
- **FR-006**: 运行时启动时 MUST 从数据库加载全部已发布 Agent 的完整配置（含关联的 Tool、Skill、MCP Server、LLM 模型信息）到内存。
- **FR-007**: 运行时 MUST 支持一次性加载与延迟加载两种模式，可通过配置项切换；延迟加载模式下，首次对某 Agent 发起对话时才完成其完整初始化。
- **FR-008**: 运行时 MUST 订阅 Redis Stream `agent.publish`；消费到发布事件后 MUST 在 10 秒内将对应 Agent 配置更新至 Agent 池。
- **FR-009**: 运行时 MUST 维护 AgentPool，为每个已发布 Agent 管理已初始化的执行实例（或实例工厂），避免每次对话重新构建。
- **FR-010**: 运行时 MUST 维护 ToolPool 和 SkillPool，缓存工具/技能的描述、执行配置及 LangChain 工具对象，避免重复序列化构建。
- **FR-011**: 运行时 MUST 维护 MCPConnectionPool，为每个 MCP Server 保持长连接；工具调用时复用已有连接，连接断开时自动重连。
- **FR-012**: 多 Agent 流水线流式调用时，若路由结果为单一子 Agent 且置信度 ≥ 配置阈值，运行时 MUST 对该子 Agent 执行真实流式调用并直接转发 SSE 事件流，不经聚合。
- **FR-013**: Agent、Tool、Skill、工作流等交互节点 MUST 以抽象基类定义统一接口（`execute`/`stream`），具体实现通过策略模式注入。
- **FR-014**: 节点实例的创建 MUST 通过工厂类（Factory）完成，不在业务逻辑中直接 `new` 具体类。
- **FR-015**: 所有公共 API 方法 MUST 提供 Google 风格 docstring（含 Args、Returns、Raises）。
- **FR-016**: 所有方法参数与返回值 MUST 有完整类型注解。
- **FR-017**: 运行时 MUST 在 Redis Stream 断连时继续用最后一次成功加载的配置提供服务，并在后台重试订阅。
- **FR-018**（P2）: 运行时 AgentPool MUST 支持配置最大容量上限；达到上限时按"加载时间权重 + 空闲时长权重"组合评分淘汰得分最低的 Agent 实例，淘汰操作 MUST 记录结构化日志（含被淘汰 Agent ID、版本、评分），为未来告警通知预留扩展接口。

### 关键数据实体

- **PublishedAgent**：已发布的 Agent 快照；属性：`publish_id`、`agent_id`、`version`、`published_at`、完整配置快照（含 tools、skills、llm_model）。
- **AgentPool**：运行时内存结构；管理 `{agent_id → AgentExecutor}` 映射，支持按版本失效与热替换。
- **ToolPool**：运行时内存结构；管理 `{tool_id → ToolDescriptor + LangChain ToolObject}` 映射。
- **SkillPool**：运行时内存结构；管理 `{skill_id → SkillDescriptor}` 映射。
- **MCPConnectionPool**：运行时内存结构；管理 `{server_endpoint → MCPSession}` 长连接映射，含健康检查与自动重连。
- **AgentPublishEvent**：Redis Stream 消息；字段：`publish_id`、`agent_id`、`version`、`timestamp`。
- **BaseNode**：所有可执行节点的抽象基类；定义 `execute(context: AgentContext) → AgentResult` 和 `stream(context: AgentContext) → AsyncIterator[StreamEvent]` 接口。
- **AgentResult**：统一的执行结果契约；包含 `answer`、`tools_called`、`latency_ms`、`session_id` 等标准字段。
- **StreamEvent**：流式 SSE 事件契约；`type` 字段枚举 `answer`/`thinking`/`tool_start`/`tool_end`/`tool_error`/`__done__`/`__error__`，与现有 SSE 协议对齐。

## 成功指标

### 可量化结果

- **SC-001**: 对已池化的 Agent 发起对话，运行时前置初始化时间（不含 LLM 推理）不超过 50ms（P95），相比当前无池化版本减少 80% 以上。
- **SC-002**: 管理端发布 Agent 后，运行时在 10 秒内完成热加载，新发布 Agent 可正常响应对话（P99）。
- **SC-003**: 同一 MCP Server 在 1 小时内累计工具调用次数 ≥ 100 次时，TCP/HTTP 连接建立次数 ≤ 5 次（含初始化与重连）。
- **SC-004**: 多 Agent 流水线中，路由识别为单一子 Agent 的流式请求，第一个 token 到达时间（TTFT）与同等配置的 SINGLE_AGENT 流水线相差不超过 200ms（P95）。
- **SC-005**: 管理端与运行时分开部署时，管理端 API 可用率不受运行时状态影响，始终保持 ≥ 99.9%。
- **SC-006**: 全量代码审查中，公共 API 方法 docstring 覆盖率 ≥ 95%，类型注解覆盖率 ≥ 98%。
- **SC-007**: 添加一种新的工具执行协议（Tool Protocol），只需新增 1 个策略类 + 1 处工厂注册，不需要修改现有节点的 `execute`/`stream` 主逻辑。

## 假设

- 管理端和运行时共享同一个数据库实例（开发：SQLite；生产：MySQL），通过 `DATABASE_URL` 环境变量切换，分开部署时通过网络访问，V1 阶段不引入数据库分离。
- Redis 已在基础设施中就绪，管理端和运行时均可访问；Redis Stream 用于发布信号，不用于会话状态存储。
- 运行时的 Agent 池大小没有严格上限（V1 阶段不引入 LRU 淘汰），所有已发布 Agent 均常驻内存。
- MCP Server 单连接可满足 V1 阶段并发需求；连接池（多连接）为 V2 优化项。
- 多 Agent 聚合场景（多子 Agent）的流式改造为 V2 优化项；V1 仅实现单路由直传流式。
- 现有的 `config_cache.py`（ConfigCache 类）将被重构为新的 AgentPool/ToolPool/SkillPool 体系，不保留原有接口。
- 编码规范（类型注解、docstring）作为本次重构的交付质量标准，覆盖新增或修改的所有文件。
