# 研究报告：Backend 管理端/运行时拆分与 Agent 编排池化重构

**功能分支**: `003-backend-split-runtime` | **日期**: 2026-05-06

---

## 1. Redis Streams 消费策略

**决策**: 使用 XREAD（单消费者模式），启动时以 `$` 跳过积压，正常运行时追踪上次读取的 ID。

**理由**:
- XREADGROUP（消费者组）适合多消费者负载均衡场景；运行时是单消费者，不需要消费者组复杂度
- 启动时用 `$` 表示"只消费此刻之后的消息"，配合 DB 全量加载保证数据完整
- 正常运行时追踪 `last_id`，用 `XREAD BLOCK 1000 COUNT 100 STREAMS agent:publish {last_id}` 增量消费

**De-duplication 策略**（同一 agent_id 多条积压）:
- 按 `publish_id` 降序排列，只处理每个 `agent_id` 的最大 `publish_id` 对应的事件
- 实现：消费到一批事件后，按 `agent_id` 分组取 max `publish_id`，批量更新 AgentPool

**代码模式**:
```python
# 启动时
last_id = "$"

# 事件循环
results = await redis.xread({"agent:publish": last_id}, block=1000, count=100)
if results:
    events = results[0][1]       # [(id, fields), ...]
    last_id = events[-1][0]      # 更新游标
    await process_events(deduplicate(events))
```

**备选方案（已评估，不采用）**:
- XREADGROUP: 增加消费者组管理复杂度，V1 单消费者不值
- Redis Pub/Sub: 不持久化，重启期间事件丢失（虽然本设计靠 DB 兜底，但 Stream 天然可回放是额外保障）

---

## 2. LangGraph CompiledStateGraph 实例复用安全性

**决策**: `create_deep_agent` 返回的 `CompiledStateGraph` 实例可安全跨请求复用。

**理由**:
- `CompiledStateGraph` 编译态是纯粹的 Python 可调用对象，不持有任何对话状态
- 每次 `ainvoke({"messages": [...]})` 创建独立的执行上下文（`RunnableConfig`）
- LangGraph 内部通过 `ChannelInvoke` 传递状态，不写全局变量
- LangChain/LangGraph 官方文档明确说明同一 graph 实例可并发调用

**实际验证**: 在 `single_agent.py` 中已用 `deep_agent.astream_events(...)` 多次调用，实例创建是可复用的设计前提。

**AgentPool 复用模式**:
```python
# 每个 AgentPoolEntry 持有一个已编译的 deep_agent 实例
entry: AgentPoolEntry = agent_pool.get(agent_id)
# 并发请求直接调用同一实例，无锁（各请求状态完全隔离）
result = await entry.compiled_graph.ainvoke({...})
```

---

## 3. asyncio.Lock 实现 MCP 单连接串行化

**决策**: 每个 MCP Server 端点维护一个 `asyncio.Lock`，所有工具调用通过该 Lock 串行化。

**理由**:
- MCP `ClientSession` 使用 Streamable HTTP 协议，底层 HTTP/2 或 SSE 连接不保证并发安全
- asyncio.Lock 是协程级别，无线程开销，等待队列由 asyncio 事件循环调度
- 串行化保证工具调用结果不混淆，单连接可满足 V1 并发量

**实现模式**:
```python
@dataclass
class MCPEntry:
    session: ClientSession | None
    lock: asyncio.Lock
    endpoint_url: str
    connected_at: datetime | None
    last_used_at: datetime | None
    is_healthy: bool = True

async def call_tool(self, entry: MCPEntry, tool_name: str, args: dict) -> str:
    async with entry.lock:               # 串行化
        entry.last_used_at = datetime.now()
        return await entry.session.call_tool(tool_name, arguments=args)
```

**连接重建模式**:
```python
async def ensure_connected(self, entry: MCPEntry) -> None:
    if entry.is_healthy and entry.session is not None:
        return
    # 重建连接（在 lock 保护内执行）
    async with entry.lock:
        if entry.session is None or not entry.is_healthy:
            entry.session = await self._create_session(entry.endpoint_url)
            entry.is_healthy = True
            entry.connected_at = datetime.now()
```

**后续扩展点**: MCPEntry 可替换为 `MCPConnectionPool`（持有 `list[ClientSession]` + `asyncio.Semaphore`），不改接口。

---

## 4. Agent Pool 淘汰评分策略

**决策**: 线性加权评分 `score = 0.3 × age_hours + 0.7 × idle_hours`，得分最高者淘汰。

**理由**:
- 访问时间（idle_hours）权重更高（0.7）：长期未访问的 Agent 优先淘汰，符合 LRU 直觉
- 加载时间（age_hours）权重较低（0.3）：偶尔访问的老 Agent 也有一定被淘汰的可能性
- 线性公式足够简单，便于审计日志输出，无需维护堆/树结构

**实现模式**:
```python
def eviction_score(self, entry: AgentPoolEntry) -> float:
    now = datetime.now()
    age_h = (now - entry.loaded_at).total_seconds() / 3600
    idle_h = (now - entry.last_accessed_at).total_seconds() / 3600
    return 0.3 * age_h + 0.7 * idle_h

def evict_one(self) -> int:
    """淘汰得分最高的条目，返回被淘汰的 agent_id。"""
    victim_id = max(self._pool, key=lambda k: self.eviction_score(self._pool[k]))
    entry = self._pool.pop(victim_id)
    logger.info(
        "agent_pool.evict",
        extra={"agent_id": victim_id, "version": entry.version,
               "score": self.eviction_score(entry)}   # structured log
    )
    return victim_id
```

**告警预留接口**:
```python
class AgentEvictionEvent:
    agent_id: int
    version: int
    score: float
    reason: str

# hook 预留，V1 为空实现
async def on_eviction(self, event: AgentEvictionEvent) -> None:
    pass   # V2 接入告警
```

---

## 5. 多 Agent 单路由直传流式输出

**决策**: 在 `MultiAgentNode.stream()` 中，当路由返回单一子 Agent 且置信度 ≥ 阈值时，直接调用子 Agent 的 `stream()` 方法并透传所有事件。

**问题背景**: 当前 `execute_stream_query` 中 MULTI_AGENT 路径调用非流式 `execute_query` 后以单个 `answer` 事件推送，导致流式体验退化。

**实现设计**:
```python
async def stream(self, context: AgentContext) -> AsyncIterator[StreamEvent]:
    route = await route_multi_agent(
        context.query, sub_agents, orchestrator_llm, threshold
    )
    
    if route.is_single and route.confidence >= threshold:
        # 单路由直传：sub-agent 流式事件直接 yield
        target = sub_agents_map[route.target_agent_ids[0]]
        async for event in target.stream(context):
            yield event   # 所有 StreamEvent 类型透传，包括 tool_start/end
        return
    
    # 多路由：串行执行 + 聚合（现有逻辑，非流式）
    result = await self.execute(context)
    yield StreamEvent(type="answer", content=result.answer)
    yield StreamEvent(type="__done__", **result.to_dict())
```

**后置检测时序**: 在外层 dispatcher 中，单路由直传时 `__done__` 事件的 `answer` 字段触发后置检测，检测失败则推送 `error` 事件（与单 Agent 模式一致）。

---

## 6. FastAPI 双应用入口设计

**决策**: 共享 `backend/src/` 代码包，通过两个独立 `main_*.py` 入口文件注册不同路由子集。

**理由**:
- 不引入新的包结构（YAGNI），现有 models/core/services 全部复用
- 管理端启动：`uvicorn src.main_management:app`（包含所有 CRUD 路由，不含 query）
- 运行时启动：`uvicorn src.main_runtime:app`（仅包含 query 路由 + 池初始化）
- 两个应用共享同一个数据库实例

**管理端 vs 运行时路由对比**:

| 路由模块 | 管理端 | 运行时 |
|---------|--------|--------|
| `/api/v1/agents` (CRUD) | ✅ | ❌ |
| `/api/v1/agents/{id}/publish` | ✅ | ❌ |
| `/api/v1/tools` | ✅ | ❌ |
| `/api/v1/skills` | ✅ | ❌ |
| `/api/v1/pipelines` | ✅ | ❌ |
| `/api/v1/mcp-servers` | ✅ | ❌ |
| `/api/v1/detection-rules` | ✅ | ❌ |
| `/api/v1/models` | ✅ | ❌ |
| `/api/v1/marketplace` | ✅ | ❌ |
| `/api/v1/events` | ✅ | ❌ |
| `/api/v1/query` | ❌ | ✅ |

---

所有关键技术决策已确认，无 NEEDS CLARIFICATION 残留。
