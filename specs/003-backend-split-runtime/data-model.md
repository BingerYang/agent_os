# 数据模型：Backend 管理端/运行时拆分与 Agent 编排池化重构

**功能分支**: `003-backend-split-runtime` | **日期**: 2026-05-06

---

## 一、数据库模型变更

### 新增表：`agent_publishes`

记录每次 Agent 发布操作的快照，是运行时加载 Agent 配置的唯一来源。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | BIGINT | PK, AUTO_INCREMENT | 发布记录 ID（即 `publish_id`） |
| `agent_id` | BIGINT | FK → agents.id, NOT NULL | 被发布的 Agent |
| `version` | INT | NOT NULL, DEFAULT 1 | 发布版本号，每次发布递增 |
| `config_snapshot` | JSON | NOT NULL | 完整配置快照（见下方结构） |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | 是否为该 Agent 的当前生效版本 |
| `published_at` | DATETIME | NOT NULL | 发布时间 |
| `published_by` | VARCHAR(100) | NULL | 操作者标识（可选） |
| `created_at` | DATETIME | NOT NULL | |
| `updated_at` | DATETIME | NOT NULL | |

**索引**: `(agent_id, is_active)` 联合索引，用于快速查找某 Agent 的当前生效版本。

**`config_snapshot` JSON 结构**:
```json
{
  "agent_id": 1,
  "name": "示例智能体",
  "agent_type": "SINGLE",
  "system_prompt": "你是一个...",
  "temperature": 0.7,
  "max_tokens": 2048,
  "llm_model": {
    "id": 1,
    "model_id": "gpt-4o",
    "endpoint_url": "https://...",
    "api_key_encrypted": "AES_GCM_ENCRYPTED..."
  },
  "tools": [
    {
      "id": 1,
      "name": "weather_tool",
      "display_name": "天气查询",
      "description": "...",
      "protocol": "MCP",
      "endpoint_url": null,
      "mcp_tool_name": "get_weather",
      "auth_type": "NONE",
      "auth_config": {},
      "mcp_server": {
        "id": 1,
        "endpoint_url": "http://mcp-server:8000/mcp",
        "auth_type": "NONE",
        "auth_config": {},
        "headers": {}
      }
    }
  ],
  "skills": [
    {
      "id": 1,
      "name": "research_skill",
      "description": "...",
      "tool_ids": [1, 2]
    }
  ],
  "sub_agent_ids": [],
  "route_confidence_threshold": 0.7,
  "timeout_seconds": 30
}
```

### 修改表：`agents`（新增字段）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `published_version` | INT | NULL, DEFAULT NULL | 当前已发布的版本号；NULL 表示从未发布 |
| `last_published_at` | DATETIME | NULL | 最近一次发布时间 |

---

## 二、运行时内存数据结构

以下结构存在于运行时进程内存中，重启时从数据库重新构建。

### AgentPoolEntry（Agent 池条目）

```python
@dataclass
class AgentPoolEntry:
    agent_id: int
    version: int                          # 来自 AgentPublish.version
    agent_type: AgentType                 # SINGLE / MULTI
    compiled_graph: CompiledStateGraph    # deepagents 返回的可复用实例
    lc_tools: list[StructuredTool]        # 已构建的 LangChain 工具列表
    system_prompt: str
    llm_config: LLMConfig                 # 解密后的 LLM 连接参数
    sub_agent_ids: list[int]              # MULTI 类型时的子 Agent ID 列表
    route_confidence_threshold: float     # 路由置信度阈值
    timeout_seconds: int
    loaded_at: datetime                   # 首次加载时间（用于淘汰评分）
    last_accessed_at: datetime            # 最近一次被调用时间（用于淘汰评分）
    access_count: int                     # 累计调用次数
```

### ToolPoolEntry（工具池条目）

```python
@dataclass
class ToolPoolEntry:
    tool_id: int
    lc_tool: StructuredTool              # 已构建的 LangChain 工具（含实际调用逻辑）
    protocol: ToolProtocol               # MCP / HTTP / BUILTIN
    mcp_server_endpoint: str | None      # MCP 工具对应的 Server 端点
    loaded_at: datetime
```

### SkillPoolEntry（技能池条目）

```python
@dataclass
class SkillPoolEntry:
    skill_id: int
    name: str
    description: str
    tool_ids: list[int]                  # 关联工具（从 ToolPool 查找）
    loaded_at: datetime
```

### MCPEntry（MCP 长连接条目）

```python
@dataclass
class MCPEntry:
    endpoint_url: str
    session: ClientSession | None        # None 表示未连接
    lock: asyncio.Lock                   # 串行化并发调用
    headers: dict[str, str]              # 认证请求头
    connected_at: datetime | None
    last_used_at: datetime | None
    is_healthy: bool = True
```

### PipelineCacheEntry（流水线配置缓存）

```python
@dataclass
class PipelineCacheEntry:
    pipeline_uid: str
    pipeline_id: int
    pipeline_type: PipelineType          # SINGLE_AGENT / MULTI_AGENT
    primary_agent_id: int
    detection_rule_ids: list[int]        # 关联的检测规则 ID
    route_confidence_threshold: float
    timeout_seconds: int
    enabled: bool
```

### AgentPublishEvent（Redis Stream 消息结构）

```python
# Redis XADD 写入，XREAD 读取，字段均为 str
class AgentPublishEvent:
    publish_id: str      # AgentPublish.id
    agent_id: str        # Agent.id
    version: str         # AgentPublish.version
    timestamp: str       # ISO8601
```

---

## 三、BaseNode 及节点抽象体系

### 抽象基类层次

```
BaseNode (ABC)
├── SingleAgentNode        # 单 Agent 执行（SINGLE_AGENT 流水线）
└── MultiAgentNode         # 多 Agent 编排（MULTI_AGENT 流水线）

BaseToolStrategy (ABC)
├── MCPToolStrategy        # MCP 协议工具执行
├── HTTPToolStrategy       # HTTP 协议工具执行
└── BuiltinToolStrategy    # 内置工具执行（占位）
```

### AgentContext（执行上下文，注入给 BaseNode）

```python
@dataclass
class AgentContext:
    query: str
    session_id: str
    pipeline_config: PipelineCacheEntry
    agent_pool: AgentPool
    tool_pool: ToolPool
    mcp_pool: MCPConnectionPool
```

### AgentResult（执行结果）

```python
@dataclass
class AgentResult:
    answer: str
    tools_called: list[str]
    session_id: str
    latency_ms: int
    pipeline_type: str
    sub_results: list[dict] | None = None   # 多 Agent 时填充
```

### StreamEvent（流式事件，与现有 SSE 事件对齐）

```python
@dataclass
class StreamEvent:
    type: str    # answer | thinking | tool_start | tool_end | tool_error | __done__ | __error__
    content: str | None = None
    tool: str | None = None
    output: str | None = None
    message: str | None = None
    # __done__ 时包含完整 AgentResult 字段
    answer: str | None = None
    tools_called: list[str] | None = None
    session_id: str | None = None
    latency_ms: int | None = None
```

---

## 四、运行时数据流

```
startup:
  DB → PipelineCache (all enabled pipelines)
  DB → DetectionCache (all enabled rules)
  DB → AgentPublish(is_active=True) → AgentPool + ToolPool + SkillPool
  for each MCP server in ToolPool → MCPConnectionPool (lazy/eager per config)
  Redis XREAD "$" → 开始订阅

conversation request (POST /api/v1/query):
  1. PipelineCache.get(pipeline_uid)          # no DB
  2. DetectionCache.get(rule_ids)             # no DB
  3. run_pre_detection(query, rules)
  4. AgentPool.get(primary_agent_id)          # no DB
  5. SingleAgentNode.execute/stream(context)  # no DB; MCP via MCPConnectionPool
  6. run_post_detection(answer, rules)
  7. return result / stream events

redis event (background):
  1. parse AgentPublishEvent
  2. deduplicate by agent_id → keep max publish_id
  3. DB.fetch(AgentPublish, publish_id)       # background, not conversation
  4. AgentPool.update(agent_id, new_entry)
  5. ToolPool.update(new_tools)
  6. MCPConnectionPool.refresh(changed_endpoints)
```
