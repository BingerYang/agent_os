# API 接口契约：Agent 调度平台

**版本**: v1 | **前缀**: `/api/v1/` | **日期**: 2026-04-18

## 通用规范

### 响应体格式

所有接口响应统一格式（Constitution I）：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "timestamp": "2026-04-18T10:00:00Z"
}
```

- `code = 0`：成功；非 0：业务错误
- 错误示例：`{"code": 40001, "message": "工具名称已存在", "data": null, "timestamp": "..."}`

### 分页参数（列表接口统一）

查询参数：`?page=1&page_size=20`
响应 `data` 格式：
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

---

## 查询入口

### POST /api/v1/query

提交用户查询，触发 Agent 调度流水线。

**请求体**:
```json
{
  "query": "今天北京的天气怎么样？",
  "pipeline_id": 1,
  "stream": false,
  "session_id": "optional-session-id"
}
```

**响应**（非流式）:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "answer": "今天北京天气晴，气温 18-26°C，适合出行。",
    "pipeline_type": "SINGLE_AGENT",
    "tools_called": ["weather_query"],
    "session_id": "sess_abc123",
    "latency_ms": 1240
  },
  "timestamp": "2026-04-18T10:00:00Z"
}
```

**响应**（流式，`stream: true`）：`Content-Type: text/event-stream`，逐 token 推送。

**错误码**:
- `40301`：前置检测拦截，`message` 包含拒绝说明
- `40302`：后置检测拦截，返回安全提示
- `40401`：指定 pipeline_id 不存在或未启用
- `50001`：所有工具均无法匹配意图

---

## Agent 管理

### GET /api/v1/agents

列表查询 Agent，支持筛选。

**查询参数**: `?agent_type=SINGLE&enabled=true&keyword=财神&page=1&page_size=20`

### POST /api/v1/agents

创建 Agent。

**请求体**:
```json
{
  "name": "财神助手",
  "description": "财神场景专用 Agent",
  "agent_type": "SINGLE",
  "source_platform": "local",
  "llm_model_id": 1,
  "system_prompt": "你是一个专业的财神助手...",
  "tool_ids": [1, 2, 3],
  "skill_ids": [1]
}
```

### GET /api/v1/agents/{id}

获取 Agent 详情（含关联 Tool、Skill 列表）。

### PUT /api/v1/agents/{id}

全量更新 Agent。

### DELETE /api/v1/agents/{id}

删除 Agent（需确认无 Pipeline 引用）。

### PATCH /api/v1/agents/{id}/toggle

切换启用状态，触发配置变更事件。

**请求体**: `{"enabled": true}`

---

## Tool 管理

### GET /api/v1/tools

列表查询，支持 `?protocol=MCP&enabled=true&keyword=天气`

### POST /api/v1/tools

**请求体**:
```json
{
  "name": "weather_query",
  "display_name": "天气查询服务",
  "description": "查询指定城市的实时天气",
  "protocol": "MCP",
  "endpoint_url": "http://mcp-server:8080/weather",
  "input_schema": {
    "type": "object",
    "properties": {
      "city": {"type": "string", "description": "城市名称"}
    },
    "required": ["city"]
  },
  "output_schema": {"type": "object"},
  "tags": ["生活服务", "官方预置"],
  "version": "v1.0.5"
}
```

### GET /api/v1/tools/{id}
### PUT /api/v1/tools/{id}
### DELETE /api/v1/tools/{id}
### PATCH /api/v1/tools/{id}/toggle

---

## Skill 管理

### GET /api/v1/skills
### POST /api/v1/skills

**请求体**:
```json
{
  "name": "fortune_greeting",
  "description": "根据场景生成传统祈福祝寿话术",
  "trigger_condition": "用户提及祈福、祝寿、财运相关意图",
  "tool_ids": [1, 2],
  "tags": ["官方预置", "文化"],
  "version": "v1.3.0"
}
```

### GET /api/v1/skills/{id}
### PUT /api/v1/skills/{id}
### DELETE /api/v1/skills/{id}
### PATCH /api/v1/skills/{id}/toggle

---

## Pipeline 管理

### GET /api/v1/pipelines
### POST /api/v1/pipelines

**请求体**:
```json
{
  "name": "财神场景单Agent流水线",
  "pipeline_type": "SINGLE_AGENT",
  "primary_agent_id": 1,
  "route_confidence_threshold": 0.7,
  "timeout_seconds": 30,
  "stream_output": false,
  "detection_rule_ids": [1, 2]
}
```

### GET /api/v1/pipelines/{id}
### PUT /api/v1/pipelines/{id}
### DELETE /api/v1/pipelines/{id}
### PATCH /api/v1/pipelines/{id}/toggle

---

## 前置/后置检测规则管理

### GET /api/v1/detection-rules

**查询参数**: `?stage=PRE&rule_type=keyword&enabled=true`

### POST /api/v1/detection-rules

**请求体**:
```json
{
  "name": "违禁词过滤",
  "stage": "PRE",
  "rule_type": "keyword",
  "rule_content": {
    "patterns": ["赌博", "欺诈"],
    "mode": "any"
  },
  "reject_message": "您的请求包含不当内容，已被系统拦截。",
  "priority": 10
}
```

### GET /api/v1/detection-rules/{id}
### PUT /api/v1/detection-rules/{id}
### DELETE /api/v1/detection-rules/{id}
### PATCH /api/v1/detection-rules/{id}/toggle

---

## 商场管理

### GET /api/v1/marketplace

浏览商场条目（Tool / Skill / Agent 统一视图）。

**查询参数**: `?item_type=tool&enabled=true&keyword=天气&tag=官方预置`

**响应 data.items 示例**:
```json
[
  {
    "item_type": "tool",
    "item_id": 3,
    "name": "天气查询服务",
    "description": "实时天气查询，支持全球城市",
    "source_platform": "local",
    "tags": ["第三方集成"],
    "version": "v1.0.5",
    "enabled": false
  }
]
```

### POST /api/v1/marketplace/{item_type}/{item_id}/install

安装/启用子系统，`item_type` 为 `tool` / `skill` / `agent`。

**响应**: 返回更新后的条目信息，同时触发 ConfigChangeEvent 推送运行时。

### DELETE /api/v1/marketplace/{item_type}/{item_id}/install

卸载/禁用子系统，同时触发 ConfigChangeEvent。

### POST /api/v1/marketplace/agents

注册第三方 Agent。

**请求体**:
```json
{
  "name": "第三方天气Agent",
  "description": "通过第三方平台接入的天气智能体",
  "source_platform": "weather-platform",
  "access_url": "https://api.weather-agent.com/invoke",
  "access_token": "Bearer xxx"
}
```

系统在保存前执行连通性验证（`POST access_url` with ping payload）。

---

## 模型配置管理

### GET /api/v1/models

**查询参数**: `?supplier=OpenAI&status=configured&keyword=gpt`

### POST /api/v1/models

**请求体**:
```json
{
  "name": "GPT-4 Turbo",
  "model_id": "gpt-4-turbo",
  "supplier": "OpenAI",
  "category": "GPT系列",
  "endpoint_url": "",
  "api_key": "sk-xxx",
  "api_version": "gpt-4-turbo",
  "description": "OpenAI GPT-4 Turbo 模型"
}
```

### GET /api/v1/models/{id}
### PUT /api/v1/models/{id}
### DELETE /api/v1/models/{id}

---

## 配置快照与事件流

### GET /api/v1/config/snapshot

运行时启动时调用，获取完整配置快照。

**响应 data**:
```json
{
  "agents": [...],
  "tools": [...],
  "skills": [...],
  "detection_rules": [...],
  "snapshot_at": "2026-04-18T10:00:00Z"
}
```

### GET /api/v1/events/stream

SSE 长连接，运行时订阅配置变更推送。

**响应格式** (`text/event-stream`):
```
event: config_change
data: {"event_type": "tool.enabled", "object_type": "tool", "object_id": 3, "change_summary": {"enabled": true}, "created_at": "2026-04-18T10:01:00Z"}

event: ping
data: {}
```

**重连策略**: 客户端断线后自动重连，重连时携带 `Last-Event-ID` 请求头，服务端返回断线期间的积压事件。

---

## 错误码规范

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| 40001 | 400 | 请求参数校验失败 |
| 40101 | 401 | 未认证 |
| 40301 | 403 | 前置检测拦截 |
| 40302 | 403 | 后置检测拦截 |
| 40401 | 404 | 资源不存在 |
| 40901 | 409 | 资源冲突（如名称重复） |
| 42201 | 422 | 业务逻辑校验失败（如 Agent 仍被 Pipeline 引用） |
| 50001 | 500 | 服务内部错误 |
| 50201 | 502 | 第三方工具/Agent 不可达 |
| 50801 | 508 | 子 Agent 响应超时 |
