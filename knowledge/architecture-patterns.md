# Agent OS 架构模式

**验证日期**: 2026-05-14
**来源**: specs/001～003 research.md + 代码实现归纳

---

## 目录

1. [单 Agent 流水线](#1-单-agent-流水线)
2. [多 Agent 流水线](#2-多-agent-流水线)
3. [框架层次映射](#3-框架层次映射)
4. [SSE 事件总线（管理端 → 运行时通知）](#4-sse-事件总线)
5. [运行时配置热加载流程](#5-运行时配置热加载流程)

---

## 1. 单 Agent 流水线

```
用户查询
  │
  ▼
run_pre_detection(pre_rules, query)        ← query_service.py，LangGraph 外
  │ 通过（query 可能已被改写）
  ▼
node.execute(agent_ctx)                    ← CompiledStateGraph.ainvoke()
  │   └─ 意图识别 + 工具选择（LLM + planning tool）
  │   └─ 工具调用循环（MCP / HTTP 工具）
  │   └─ 结果汇总（LLM）
  │ 返回 answer
  ▼
run_post_detection(post_rules, answer)     ← query_service.py，LangGraph 外
  │ 通过（answer 可能已被改写，或挂起等待审批）
  ▼
返回调用方
```

**关键点**：前后置检测在 `query_service.py` 中包裹 `node.execute()`，不侵入 LangGraph 图结构。

---

## 2. 多 Agent 流水线

```
用户查询
  │
  ▼
run_pre_detection(pre_rules, query)
  │
  ▼
intent_router（LangChain create_agent + 路由 prompt）
  │
  ├─ 置信度 ≥ 阈值 → 单个 create_deep_agent 实例
  │                    └─ 返回 answer
  │
  └─ 置信度 < 阈值 → LangGraph StateGraph
                       ├─ 子 Agent A（create_deep_agent）
                       ├─ 子 Agent B（create_deep_agent）
                       └─ 结果聚合节点
  │
  ▼
run_post_detection(post_rules, answer)
  │
  ▼
返回调用方
```

**框架分工**：
- 意图路由节点：`langchain.agents.create_agent`（轻量，仅需 LLM 判断）
- 业务 Agent 节点：`deepagents.create_deep_agent`（开箱即用复杂能力）
- 编排层：`langgraph.StateGraph`（并行 / 串行 / 条件路由）

---

## 3. 框架层次映射

| 本项目模块 | 使用的框架组件 | 说明 |
|-----------|-------------|------|
| `agents/single_agent.py` | `deepagents.create_deep_agent` | 主 Agent 执行引擎 |
| `agents/multi_agent.py` | `langgraph.StateGraph` + 多个 `create_deep_agent` | 多 Agent 编排 |
| `agents/intent_router.py` | LangChain 1.0 `create_agent` | 轻量路由，不需要 DeepAgents 能力 |
| `agents/detection.py` | 纯 Python 函数 + STRATEGY_REGISTRY | 外层包裹，LangGraph 外 |
| `services/query_service.py` | 编排前后置检测与 Agent 执行 | 最外层流程控制 |

---

## 4. SSE 事件总线

**场景**：管理端配置变更（启用工具、修改 Agent 参数）→ 实时推送给运行时热加载。

**技术选型**（来自 001 research.md）：

| 方案 | 评估 |
|------|------|
| **SSE + 内存 asyncio.Queue**（当前） | ✅ HTTP 原生，零额外基础设施，单进程内广播 |
| Redis Pub/Sub | ⚠️ V1 阶段增加部署复杂度，预留为扩展方案 |
| WebSocket | ❌ 双向通信过重，推送场景不需要双向 |
| DB 轮询 | ❌ 违反管理端/运行时解耦要求 |

**实现模式**：
```python
# 管理端写操作完成后发布事件
await event_bus.publish(ConfigChangeEvent(
    type="tool.enabled",
    object_id=tool_id,
    ...
))

# 运行时 SSE 端点：GET /api/v1/events/stream
async for event in event_bus.subscribe():
    config_cache.apply(event)
```

**升级路径**：单进程 → 多进程/多实例时，将内存 `asyncio.Queue` 替换为 Redis `PUBLISH/SUBSCRIBE`，运行时消费代码**无需改动**。

---

## 5. 运行时配置热加载流程

```
运行时启动
  │
  ├─ 1. GET /api/v1/config/snapshot   ← 全量拉取当前配置
  │
  ├─ 2. GET /api/v1/events/stream     ← 建立 SSE 长连接，订阅增量变更
  │       │
  │       ├─ 收到 ConfigChangeEvent → config_cache.apply(event)
  │       │
  │       └─ 连接断开 → 自动重连（MCP 连接池同理：断线透明重连）
  │               └─ 重连后：GET /api/v1/config/snapshot?since={last_ts}（增量）
  │
  └─ 3. 管理端不可用时 → 使用最后成功缓存继续服务（fail-open）
```

**热加载延迟目标**：配置变更在 **5 秒内**对运行时生效（SC-003）。

**缓存层级**：
- `AgentPool` / `ToolPool` / `SkillPool` / `MCPConnectionPool` 各自维护本地缓存
- SSE 事件触发对应 Pool 的 `reload()` 方法，无需重启进程
