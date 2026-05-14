# API Contracts: Agent 检测规则引擎

**Feature**: 004-detection-rules
**Date**: 2026-05-14
**Base Path**: `/api/v1`
**Response Format**: `{"code": 0, "message": "ok", "data": ..., "timestamp": ...}`

---

## 一、检测规则（DetectionRule）管理

> 现有端点 `GET/POST/PUT/DELETE/PATCH /detection-rules` 保持不变，新增字段兼容

### 扩展后的 Rule 对象结构

```json
{
  "id": 1,
  "name": "限流防刷-全局",
  "stage": "PRE",
  "strategy_type": "rate_limit",
  "rule_type": "keyword",
  "action_type": "block",
  "max_retry_count": 3,
  "rule_content": {
    "window_seconds": 60,
    "max_requests": 100,
    "key_by": "user"
  },
  "reject_message": "请求频率超限，请稍后重试",
  "priority": 10,
  "enabled": true,
  "created_at": "2026-05-14T08:00:00Z",
  "updated_at": "2026-05-14T08:00:00Z"
}
```

### POST /detection-rules（新增字段）

**Request Body** （新增 `strategy_type`、`action_type`、`max_retry_count`）:
```json
{
  "name": "限流防刷-全局",
  "stage": "PRE",
  "strategy_type": "rate_limit",
  "rule_type": "keyword",
  "action_type": "block",
  "max_retry_count": 3,
  "rule_content": {"window_seconds": 60, "max_requests": 100, "key_by": "user"},
  "reject_message": "请求频率超限",
  "priority": 10
}
```

**字段说明**：
- `strategy_type`: 必填，枚举见 data-model
- `action_type`: 必填，枚举值：`block`/`rewrite`/`log_review`/`retry`/`log_only`/`degrade`/`escalate`/`alert`
- `max_retry_count`: 可选，默认 3，仅当 `action_type=retry` 时有效

---

## 二、Agent 策略绑定

### GET /agents/{agent_id}/detection-bindings

获取某 Agent 所有策略绑定（含合并后的生效配置）。

**Response**:
```json
{
  "code": 0,
  "data": {
    "agent_id": 42,
    "bindings": [
      {
        "id": 101,
        "rule_id": 1,
        "rule_name": "限流防刷-全局",
        "strategy_type": "rate_limit",
        "stage": "PRE",
        "enabled": true,
        "action_override": null,
        "priority_override": null,
        "config_override": {},
        "effective_config": {
          "window_seconds": 60,
          "max_requests": 50,
          "key_by": "user"
        },
        "effective_action": "block",
        "effective_priority": 10
      }
    ]
  }
}
```

---

### POST /agents/{agent_id}/detection-bindings

将策略规则绑定到 Agent，并可指定 per-agent 配置覆盖。

**Request Body**:
```json
{
  "rule_id": 1,
  "enabled": true,
  "config_override": {
    "max_requests": 50
  },
  "action_override": null,
  "priority_override": null
}
```

**Response**: 201，返回绑定对象

---

### PUT /agents/{agent_id}/detection-bindings/{binding_id}

更新 Agent 的策略绑定配置（覆盖参数、动作、优先级）。

**Request Body**:
```json
{
  "enabled": true,
  "config_override": {"max_requests": 200},
  "action_override": "log_review",
  "priority_override": 5
}
```

---

### DELETE /agents/{agent_id}/detection-bindings/{binding_id}

解除 Agent 的策略绑定。

**Response**: `{"code": 0, "data": null, "message": "解绑成功"}`

---

### PATCH /agents/{agent_id}/detection-bindings/{binding_id}/toggle

快速开关某 Agent 的某条策略绑定。

**Request Body**: `{"enabled": false}`

---

### GET /agents/{agent_id}/detection-bindings/summary

获取 Agent 的策略覆盖概览（前置/后置分组，用于 UI 展示）。

**Response**:
```json
{
  "code": 0,
  "data": {
    "pre_checks": [
      {"strategy_type": "rate_limit", "name": "限流防刷", "enabled": true, "binding_id": 101},
      {"strategy_type": "identity_verify", "name": "身份校验", "enabled": false, "binding_id": null}
    ],
    "post_checks": [
      {"strategy_type": "privacy_leak", "name": "后置隐私防泄密", "enabled": true, "binding_id": 202}
    ]
  }
}
```
- `binding_id = null` 表示该策略未绑定到此 Agent（未启用）

---

## 三、检测事件审计日志

### GET /detection-events

分页查询检测事件记录。

**Query Parameters**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | int | 按 Agent 筛选 |
| `strategy_type` | string | 按策略类型筛选 |
| `action_taken` | string | 按处置动作筛选 |
| `status` | string | 按状态筛选（LOGGED/PENDING_REVIEW/REVIEWED/ESCALATED/RESOLVED）|
| `stage` | string | PRE / POST |
| `start_time` | datetime | 时间范围起 |
| `end_time` | datetime | 时间范围止 |
| `page` | int | 默认 1 |
| `page_size` | int | 默认 20，最大 100 |

**Response**:
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": 1001,
        "agent_id": 42,
        "agent_name": "客服 Agent",
        "rule_id": 1,
        "rule_name": "限流防刷-全局",
        "session_id": "sess_abc123",
        "stage": "PRE",
        "strategy_type": "rate_limit",
        "action_taken": "block",
        "hit_detail": {"reason": "超出 60s 内 100 次限制", "current_count": 101},
        "input_snapshot": "用户输入摘要...",
        "status": "LOGGED",
        "created_at": "2026-05-14T10:00:00Z"
      }
    ],
    "total": 128,
    "page": 1,
    "page_size": 20
  }
}
```

---

### GET /detection-events/{event_id}

获取单条事件详情。

---

### PATCH /detection-events/{event_id}/review

提交人工复核结果（仅 status=PENDING_REVIEW 或 ESCALATED 的记录可操作）。

**Request Body**:
```json
{
  "status": "REVIEWED",
  "reviewer_note": "已确认为误报，加入白名单"
}
```

---

## 四、策略配置变更审计

### GET /policy-config-audits

分页查询配置变更记录。

**Query Parameters**:
| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | int | 按 Agent 筛选（null 则查全局变更）|
| `rule_id` | int | 按规则筛选 |
| `change_type` | string | CREATE/UPDATE/DELETE/ENABLE/DISABLE/BIND/UNBIND |
| `operator_id` | string | 按操作人筛选 |
| `start_time` | datetime | 时间范围 |
| `end_time` | datetime | 时间范围 |
| `page` | int | 默认 1 |
| `page_size` | int | 默认 20 |

**Response**:
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": 501,
        "operator_id": "admin",
        "agent_id": 42,
        "agent_name": "客服 Agent",
        "rule_id": 1,
        "rule_name": "限流防刷-全局",
        "change_type": "BIND",
        "before_value": null,
        "after_value": {"enabled": true, "config_override": {"max_requests": 50}},
        "created_at": "2026-05-14T09:30:00Z"
      }
    ],
    "total": 42,
    "page": 1,
    "page_size": 20
  }
}
```

---

## 五、策略枚举查询（辅助接口）

### GET /detection-rules/meta

返回所有策略类型的元信息，供前端渲染配置表单。

**Response**:
```json
{
  "code": 0,
  "data": {
    "strategy_types": [
      {
        "value": "rate_limit",
        "label": "限流防刷",
        "code": "P-01",
        "stage": "PRE",
        "description": "基于用户/IP/Agent 维度的请求频率控制",
        "config_schema": {
          "window_seconds": {"type": "integer", "label": "时间窗口(秒)", "default": 60},
          "max_requests": {"type": "integer", "label": "最大请求数", "default": 100},
          "key_by": {"type": "select", "options": ["user", "ip", "agent"], "default": "user"}
        }
      }
    ],
    "action_types": [
      {"value": "block", "label": "拦截"},
      {"value": "rewrite", "label": "改写"},
      {"value": "log_review", "label": "记录 Review（可继续）"},
      {"value": "retry", "label": "重试"},
      {"value": "log_only", "label": "记录（仅记录）"},
      {"value": "degrade", "label": "降级"},
      {"value": "escalate", "label": "转人工"},
      {"value": "alert", "label": "告警"}
    ]
  }
}
```
