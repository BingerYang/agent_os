# Data Model: Agent 检测规则引擎

**Feature**: 004-detection-rules
**Date**: 2026-05-14

---

## 实体关系概览

```
Agent (已有)
  └── AgentDetectionBinding (新增，多对多关联+覆盖配置)
        └── DetectionRule (已有，扩展 strategy_type/action_type)
              └── DetectionEvent (新增，策略命中审计日志)
                    └── PolicyConfigAudit (新增，配置变更审计)
```

---

## 现有模型扩展

### DetectionRule（扩展）

| 字段 | 类型 | 状态 | 说明 |
|------|------|------|------|
| id | BIGINT PK | 已有 | |
| name | VARCHAR(128) | 已有 | 策略显示名称 |
| stage | ENUM(PRE, POST) | 已有 | 前置/后置 |
| rule_type | ENUM(keyword, llm_judge) | 已有 | 底层检测方式 |
| **strategy_type** | ENUM | **新增** | 11 种策略类型（见下表） |
| **action_type** | ENUM | **新增** | 8 种处置动作（全局默认） |
| **max_retry_count** | INT DEFAULT 3 | **新增** | `retry` action 最大重试次数 |
| rule_content | JSON | 已有 | 全局默认配置（策略参数） |
| reject_message | VARCHAR(512) | 已有 | block 时的返回消息 |
| priority | INT DEFAULT 100 | 已有 | 执行顺序（升序） |
| enabled | BOOLEAN DEFAULT TRUE | 已有 | 全局启用开关 |
| created_at | DATETIME | 已有 | |
| updated_at | DATETIME | 已有 | |

**strategy_type 枚举值**：

| 枚举值 | 编号 | 阶段 | 对应策略 |
|--------|------|------|---------|
| `rate_limit` | P-01 | PRE | 限流防刷 |
| `identity_verify` | P-02 | PRE | 身份校验 |
| `content_filter` | P-03 | PRE | 违规内容拦截 |
| `prompt_injection` | P-04 | PRE | Prompt 注入防护 |
| `pii_desensitize` | P-05 | PRE | 隐私信息前置脱敏 |
| `intent_compliance` | P-06 | PRE | 意图&业务范围合规 |
| `rbac_check` | P-07 | PRE | RBAC 权限前置校验 |
| `business_rule` | P-08 | PRE | 业务前置硬性规则 |
| `privacy_leak` | A-01 | POST | 后置隐私防泄密 |
| `result_validation` | A-02 | POST | 业务结果后置规则校验 |
| `human_approval` | A-03 | POST | 人机审批 |

**action_type 枚举值**：
`block` / `rewrite` / `log_review` / `retry` / `log_only` / `degrade` / `escalate` / `alert`

---

## 新增模型

### AgentDetectionBinding（新增）

Agent 与 DetectionRule 的绑定关系，支持 per-agent 配置覆盖。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| agent_id | BIGINT FK(agents.id) | 所属 Agent |
| rule_id | BIGINT FK(detection_rules.id) | 关联规则 |
| enabled | BOOLEAN DEFAULT TRUE | 该 Agent 上的独立开关（覆盖全局 enabled） |
| config_override | JSON | per-agent 配置覆盖（JSON Merge Patch 语义，覆盖 rule_content） |
| action_override | ENUM(action_type) NULLABLE | per-agent 处置动作覆盖，NULL 表示使用全局默认 |
| priority_override | INT NULLABLE | per-agent 执行优先级覆盖，NULL 表示使用全局 priority |
| created_at | DATETIME | |
| updated_at | DATETIME | |

**约束**：`UNIQUE(agent_id, rule_id)`

**运行时配置合并逻辑**：
```python
merged_config = {**rule.rule_content, **(binding.config_override or {})}
action = binding.action_override or rule.action_type
priority = binding.priority_override if binding.priority_override is not None else rule.priority
```

---

### DetectionEvent（新增）

所有策略命中事件的审计日志，兼做 Review Queue 和 Escalation Queue。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| agent_id | BIGINT FK(agents.id) | 触发 Agent |
| rule_id | BIGINT FK(detection_rules.id) | 命中规则 |
| session_id | VARCHAR(128) | 关联的调用会话 ID |
| stage | ENUM(PRE, POST) | 前置/后置 |
| strategy_type | VARCHAR(32) | 命中的策略类型 |
| action_taken | VARCHAR(32) | 实际执行的处置动作 |
| hit_detail | JSON | 命中详情摘要（关键词/匹配模式/LLM理由等） |
| input_snapshot | TEXT | 触发时的输入摘要（脱敏后，最多 1000 字符） |
| output_snapshot | TEXT NULLABLE | 后置策略时的输出摘要（脱敏后，最多 1000 字符） |
| status | ENUM | LOGGED / PENDING_REVIEW / REVIEWED / ESCALATED / RESOLVED |
| reviewer_id | VARCHAR(64) NULLABLE | 复核人标识（用户名） |
| reviewer_note | TEXT NULLABLE | 复核备注 |
| reviewed_at | DATETIME NULLABLE | 复核时间 |
| created_at | DATETIME | 事件发生时间 |

**状态转换**：
- `log_only` action → status = `LOGGED`（终态）
- `log_review` action → status = `PENDING_REVIEW`（可转为 `REVIEWED`）
- `escalate` action → status = `ESCALATED`（可转为 `RESOLVED`）

---

### PolicyConfigAudit（新增）

策略配置变更的操作审计记录。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| operator_id | VARCHAR(64) | 操作人标识（用户名/系统） |
| agent_id | BIGINT NULLABLE | NULL 表示全局规则变更，非 NULL 表示 Agent 绑定变更 |
| rule_id | BIGINT | 变更的规则 ID |
| change_type | ENUM | CREATE / UPDATE / DELETE / ENABLE / DISABLE / BIND / UNBIND |
| before_value | JSON NULLABLE | 变更前的值（全字段快照） |
| after_value | JSON NULLABLE | 变更后的值（全字段快照） |
| created_at | DATETIME | 操作时间 |

---

## rule_content JSON Schema（各策略）

### P-01 限流防刷
```json
{
  "window_seconds": 60,
  "max_requests": 100,
  "key_by": "user",
  "burst_limit": 20
}
```
`key_by`: `"user"` | `"ip"` | `"agent"`

### P-02 身份校验
```json
{
  "require_token_types": ["bearer"],
  "check_expiry": true,
  "allow_anonymous": false
}
```

### P-03 违规内容拦截
```json
{
  "sub_types": ["political", "pornography", "violence", "attack"],
  "keywords": ["违禁词1", "违禁词2"],
  "patterns": ["regex1"],
  "use_llm_judge": false,
  "llm_model_id": null,
  "llm_threshold": 0.8
}
```
`sub_types` 中的值：`political` / `pornography` / `violence` / `attack`

### P-04 Prompt 注入防护
```json
{
  "patterns": ["ignore previous instructions", "disregard all"],
  "injection_keywords": ["system:", "assistant:", "###"],
  "use_llm_judge": true,
  "llm_model_id": null
}
```

### P-05 隐私信息前置脱敏（A-01 同结构）
```json
{
  "pii_types": ["phone", "idcard", "email", "bankcard", "name"],
  "mask_pattern": "***",
  "partial_mask": true
}
```

### P-06 意图&业务范围合规
```json
{
  "allowed_intents": ["客服咨询", "订单查询"],
  "deny_intents": [],
  "llm_model_id": null,
  "system_prompt": "判断用户意图是否在以下允许范围内...",
  "confidence_threshold": 0.7
}
```

### P-07 RBAC 权限前置校验
```json
{
  "required_roles": ["user", "vip"],
  "required_permissions": ["agent:query"],
  "deny_roles": ["banned"],
  "degrade_roles": ["trial"]
}
```
`degrade_roles`：这些角色触发 `degrade` 而非 `block`

### P-08 业务前置硬性规则
```json
{
  "rules": [
    {"type": "time_restriction", "allowed_hours": [9, 18], "timezone": "Asia/Shanghai"},
    {"type": "geo_restriction", "allowed_regions": ["CN"], "denied_regions": []},
    {"type": "ip_blacklist", "ips": ["1.2.3.4"], "cidrs": ["10.0.0.0/8"]},
    {"type": "user_blacklist", "user_ids": ["user_123"]}
  ]
}
```

### A-02 业务结果后置规则校验
```json
{
  "field_rules": [
    {"field": "$.order_id", "required": true, "type": "string"},
    {"field": "$.amount", "required": true, "type": "number", "min": 0}
  ],
  "regex_checks": [],
  "retry_count": 2,
  "fallback_message": "结果校验失败，请重试"
}
```

### A-03 人机审批
```json
{
  "timeout_seconds": 300,
  "fallback_action": "block",
  "approver_roles": ["approver"],
  "notify_channel": "in_app"
}
```
`fallback_action`：超时后的处置，值 ∈ `action_type` 枚举

---

## 数据库迁移脚本（概要）

```sql
-- 迁移 1：扩展 detection_rules 表
ALTER TABLE detection_rules
  ADD COLUMN strategy_type VARCHAR(32) NOT NULL DEFAULT 'content_filter',
  ADD COLUMN action_type VARCHAR(32) NOT NULL DEFAULT 'block',
  ADD COLUMN max_retry_count INT NOT NULL DEFAULT 3;

-- 迁移 2：新建 agent_detection_bindings
CREATE TABLE agent_detection_bindings (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  agent_id BIGINT NOT NULL,
  rule_id BIGINT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  config_override JSON,
  action_override VARCHAR(32),
  priority_override INT,
  created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_agent_rule (agent_id, rule_id),
  FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
  FOREIGN KEY (rule_id) REFERENCES detection_rules(id) ON DELETE CASCADE
);

-- 迁移 3：新建 detection_events
CREATE TABLE detection_events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  agent_id BIGINT NOT NULL,
  rule_id BIGINT NOT NULL,
  session_id VARCHAR(128),
  stage VARCHAR(8) NOT NULL,
  strategy_type VARCHAR(32) NOT NULL,
  action_taken VARCHAR(32) NOT NULL,
  hit_detail JSON,
  input_snapshot TEXT,
  output_snapshot TEXT,
  status VARCHAR(32) NOT NULL DEFAULT 'LOGGED',
  reviewer_id VARCHAR(64),
  reviewer_note TEXT,
  reviewed_at DATETIME(6),
  created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
  INDEX idx_agent_id (agent_id),
  INDEX idx_rule_id (rule_id),
  INDEX idx_status (status),
  INDEX idx_created_at (created_at),
  FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
  FOREIGN KEY (rule_id) REFERENCES detection_rules(id) ON DELETE SET NULL
);

-- 迁移 4：新建 policy_config_audits
CREATE TABLE policy_config_audits (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  operator_id VARCHAR(64) NOT NULL,
  agent_id BIGINT,
  rule_id BIGINT NOT NULL,
  change_type VARCHAR(32) NOT NULL,
  before_value JSON,
  after_value JSON,
  created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
  INDEX idx_rule_id (rule_id),
  INDEX idx_agent_id (agent_id),
  INDEX idx_created_at (created_at)
);
```
