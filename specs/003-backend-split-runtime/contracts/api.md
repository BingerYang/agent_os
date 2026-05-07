# API 接口契约：Backend 管理端/运行时拆分与 Agent 编排池化重构

**功能分支**: `003-backend-split-runtime` | **日期**: 2026-05-06  
**基准**: 所有接口遵循 Constitution I（RESTful 规范），响应体统一为 `ApiResponse[T]`。

---

## 管理端新增接口

### 发布 Agent

**`PATCH /api/v1/agents/{id}/publish`**

将指定 Agent 的当前配置发布为运行时可用版本。操作：
1. 创建 `AgentPublish` 记录（生成快照），写入数据库
2. 将旧版本 `is_active` 置为 false
3. 更新 `agents.published_version` 和 `last_published_at`
4. 向 Redis Stream `agent:publish` 推送事件

**请求**

```
PATCH /api/v1/agents/{id}/publish
Content-Type: application/json

{}    (空请求体)
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `id` | integer | Agent ID |

**响应 200 OK**

```json
{
  "code": 0,
  "message": "发布成功",
  "data": {
    "publish_id": 42,
    "agent_id": 7,
    "version": 3,
    "published_at": "2026-05-06T10:00:00Z",
    "redis_notified": true
  },
  "timestamp": "2026-05-06T10:00:00.123Z"
}
```

**当 Redis 推送失败时（数据库写入已成功）**

```json
{
  "code": 0,
  "message": "发布成功（Redis 通知失败，运行时将在下次重启时同步）",
  "data": {
    "publish_id": 42,
    "agent_id": 7,
    "version": 3,
    "published_at": "2026-05-06T10:00:00Z",
    "redis_notified": false
  },
  "timestamp": "2026-05-06T10:00:00.123Z"
}
```

**错误响应**

| code | 说明 |
|------|------|
| 40401 | Agent 不存在 |
| 50001 | Agent 未配置 LLM 模型，无法发布 |
| 50002 | Agent 未关联任何工具，无法发布（可选校验） |

---

### 查询 Agent 发布历史

**`GET /api/v1/agents/{id}/publishes`**

**响应 200 OK**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "publish_id": 42,
        "version": 3,
        "is_active": true,
        "published_at": "2026-05-06T10:00:00Z",
        "published_by": "operator_01"
      }
    ],
    "total": 3
  },
  "timestamp": "..."
}
```

---

## 运行时接口（接口不变，实现重构）

### 提交查询（非流式）

**`POST /api/v1/query`**（接口契约与 001 版本完全一致，仅实现改用 AgentPool）

**请求**

```json
{
  "query": "北京今天天气如何？",
  "pipeline_id": "pl_abc123",
  "stream": false,
  "session_id": "sess_xyz"
}
```

**响应 200 OK**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "北京今天晴，气温 22°C。",
    "pipeline_type": "SINGLE_AGENT",
    "tools_called": ["weather_tool"],
    "session_id": "sess_xyz",
    "latency_ms": 1234
  },
  "timestamp": "..."
}
```

---

### 提交查询（流式 SSE）

**`POST /api/v1/query`** with `"stream": true`

SSE 事件流。**重构后新增行为**：多 Agent 流水线且路由识别为单子 Agent 时，事件流与单 Agent 模式完全一致（token 级流式，不再退化为批量推送）。

**SSE 事件类型**（不变，与 002 规格对齐）

```
event: message
data: {"type": "answer", "content": "北"}

event: message
data: {"type": "answer", "content": "京"}

event: message
data: {"type": "tool_start", "tool": "weather_tool"}

event: message
data: {"type": "tool_end", "tool": "weather_tool", "output": "..."}

event: message
data: {"type": "tool_error", "tool": "xxx", "message": "..."}

event: message
data: {"type": "thinking", "content": "..."}   // 思考模型专属

event: message
data: {"type": "__done__", "answer": "完整回答", "tools_called": ["weather_tool"],
       "session_id": "sess_xyz", "latency_ms": 1234}

event: message
data: {"type": "error", "code": 40301, "message": "前置检测拦截"}

event: message
data: {"type": "error", "code": 40302, "message": "后置检测拦截"}

event: message
data: {"type": "error", "code": 50000, "message": "内部错误"}
```

---

## Redis Stream 事件格式

**Stream Key**: `agent:publish`

**XADD 字段**（均为字符串）

```
publish_id   "42"
agent_id     "7"
version      "3"
timestamp    "2026-05-06T10:00:00.123456"
```

**运行时消费侧示例**

```python
results = await redis.xread({"agent:publish": last_id}, block=1000, count=100)
# results: [("agent:publish", [("1746518400000-0", {"publish_id": "42", ...})])]
```

---

## 接口变更摘要

| 接口 | 变更类型 | 说明 |
|------|---------|------|
| `PATCH /api/v1/agents/{id}/publish` | **新增** | 管理端发布 Agent |
| `GET /api/v1/agents/{id}/publishes` | **新增** | 查询发布历史 |
| `POST /api/v1/query` | **实现重构** | 接口契约不变；底层改用 AgentPool，不读 DB；多 Agent 单路由时支持真实流式 |
| 所有其他管理端 CRUD 接口 | **不变** | |
