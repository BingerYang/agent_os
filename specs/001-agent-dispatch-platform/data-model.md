# 数据模型：Agent 调度平台

**功能分支**: `001-agent-dispatch-platform` | **日期**: 2026-04-18

## 实体关系概览

```
LLMModel
  └── 被 Agent 引用（agent.llm_model_id）

Agent（type: SINGLE / ORCHESTRATOR）
  ├── 关联多个 Tool（通过 AgentTool 关联表）
  ├── 关联多个 Skill（通过 AgentSkill 关联表）
  └── 关联 Pipeline（一对一）

Agent（type: SUB）
  └── 被 Pipeline（MULTI_AGENT 类型）引用（通过 PipelineSubAgent 关联表）

Pipeline
  ├── 关联主 Agent（单 Agent 模式）
  ├── 关联多个子 Agent（多 Agent 模式，通过 PipelineSubAgent）
  └── 关联多个 DetectionRule（通过 PipelineDetectionRule 关联表）

MarketplaceItem（视图实体，不独立存表）
  └── 映射到 Tool / Skill / Agent 的商场视图
```

---

## 实体定义

### Agent

Agent 是核心调度单元，可以是单 Agent（执行工具调用）、子 Agent（被编排调用）或编排 Agent（调度多个子 Agent）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| name | VARCHAR(128) | NOT NULL, UNIQUE | Agent 名称 |
| description | TEXT | | 描述 |
| agent_type | ENUM('SINGLE','SUB','ORCHESTRATOR') | NOT NULL | 类型：单Agent/子Agent/编排Agent |
| source_platform | VARCHAR(128) | DEFAULT 'local' | 来源平台（local/第三方平台名） |
| access_url | VARCHAR(512) | | 第三方 Agent 接入地址（SUB 类型可选） |
| access_token | VARCHAR(1024) | | 接入认证 Token（加密存储） |
| llm_model_id | BIGINT | FK → LLMModel.id | 使用的 LLM 模型 |
| system_prompt | TEXT | | 系统提示词 |
| enabled | BOOLEAN | NOT NULL, DEFAULT TRUE | 启用状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**状态转换**: `disabled ↔ enabled`（运营人员在商场操作，变更通过事件总线推送运行时）

**验证规则**:
- `agent_type = SUB` 时，`access_url` 或关联工具列表二选一（本地子 Agent 或第三方接入）
- `agent_type = ORCHESTRATOR` 时，必须关联至少一个 SUB 类型 Agent
- `access_token` 加密存储，API 响应中显示为 `***-末尾4位`

---

### Tool

可调用工具，封装单一原子能力。MCP 工具和内置工具统一抽象。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| name | VARCHAR(128) | NOT NULL, UNIQUE | 工具名称（英文唯一标识） |
| display_name | VARCHAR(256) | NOT NULL | 展示名称 |
| description | TEXT | | 描述（用于 LLM 工具选择） |
| protocol | ENUM('MCP','HTTP','BUILTIN') | NOT NULL | 接入协议 |
| endpoint_url | VARCHAR(512) | | 工具服务地址（MCP/HTTP 类型） |
| input_schema | JSON | NOT NULL | 输入参数 JSON Schema |
| output_schema | JSON | | 输出结果 JSON Schema |
| source_platform | VARCHAR(128) | DEFAULT 'local' | 来源平台 |
| tags | JSON | | 标签列表（用于商场筛选） |
| version | VARCHAR(32) | DEFAULT 'v1.0.0' | 版本号 |
| enabled | BOOLEAN | NOT NULL, DEFAULT TRUE | 启用状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**验证规则**:
- `protocol = MCP` 或 `HTTP` 时，`endpoint_url` 必填
- `input_schema` 必须是合法 JSON Schema 对象

---

### Skill

技能是封装特定业务能力的执行单元，可依赖一组 Tool。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| name | VARCHAR(128) | NOT NULL, UNIQUE | 技能名称 |
| description | TEXT | | 描述 |
| trigger_condition | TEXT | | 触发条件（自然语言描述或关键词规则） |
| tags | JSON | | 标签列表 |
| version | VARCHAR(32) | DEFAULT 'v1.0.0' | 版本号 |
| enabled | BOOLEAN | NOT NULL, DEFAULT TRUE | 启用状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

---

### Pipeline

调度流水线配置，定义 Agent 类型选择逻辑和检测规则集。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| name | VARCHAR(128) | NOT NULL | 流水线名称 |
| pipeline_type | ENUM('SINGLE_AGENT','MULTI_AGENT') | NOT NULL | 流水线类型 |
| primary_agent_id | BIGINT | FK → Agent.id | 主 Agent（SINGLE_AGENT 模式） |
| route_confidence_threshold | FLOAT | DEFAULT 0.7 | 路由置信度阈值（MULTI_AGENT 模式） |
| timeout_seconds | INT | DEFAULT 30 | 子 Agent 响应超时秒数 |
| stream_output | BOOLEAN | DEFAULT FALSE | 是否启用流式输出（FR-010） |
| enabled | BOOLEAN | NOT NULL, DEFAULT TRUE | 启用状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

---

### DetectionRule

前置或后置检测规则，由运营人员配置，运行时执行。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| name | VARCHAR(128) | NOT NULL | 规则名称 |
| stage | ENUM('PRE','POST') | NOT NULL | 前置/后置 |
| rule_type | ENUM('keyword','llm_judge') | NOT NULL | 规则类型 |
| rule_content | JSON | NOT NULL | 规则内容（关键词列表或 LLM 判断提示词） |
| reject_message | VARCHAR(512) | | 拦截时返回用户的提示信息 |
| priority | INT | DEFAULT 100 | 执行优先级（越小越先执行） |
| enabled | BOOLEAN | NOT NULL, DEFAULT TRUE | 启用状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**规则内容示例**:
```json
// keyword 类型
{"patterns": ["违禁词1", "(?i)sensitive_pattern"], "mode": "any"}

// llm_judge 类型
{"prompt": "判断以下内容是否包含违规信息，返回 JSON: {\"passed\": bool, \"reason\": str}"}
```

---

### LLMModel

模型配置，供 Agent 选择调用。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| name | VARCHAR(128) | NOT NULL | 模型展示名称 |
| model_id | VARCHAR(256) | NOT NULL, UNIQUE | API 调用标识（如 gpt-4-turbo） |
| supplier | VARCHAR(128) | NOT NULL | 供应商（阿里云/OpenAI/DeepSeek 等） |
| category | VARCHAR(128) | NOT NULL | 模型类别 |
| endpoint_url | VARCHAR(512) | | API Endpoint（可选，覆盖默认值） |
| api_key | VARCHAR(1024) | NOT NULL | API Key（加密存储） |
| api_version | VARCHAR(64) | | API 版本标识（部分供应商需要） |
| description | TEXT | | 描述 |
| enabled | BOOLEAN | NOT NULL, DEFAULT TRUE | 启用状态 |
| created_at | DATETIME | NOT NULL | 创建时间 |
| updated_at | DATETIME | NOT NULL | 更新时间 |

**验证规则**: `api_key` 加密存储，响应中显示为 `供应商前缀-***-末尾4位`

---

### ConfigChangeEvent

配置变更事件，持久化事件日志，供运行时订阅和历史查询。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 主键 |
| event_type | VARCHAR(64) | NOT NULL | 变更类型（如 tool.enabled, agent.updated） |
| object_type | ENUM('agent','tool','skill','pipeline','detection_rule','llm_model') | NOT NULL | 变更对象类型 |
| object_id | BIGINT | NOT NULL | 变更对象 ID |
| change_summary | JSON | NOT NULL | 变更内容摘要（diff 或全量新值） |
| created_at | DATETIME | NOT NULL | 事件时间戳 |

**事件类型约定**:
- `{object_type}.created` / `.updated` / `.deleted`
- `{object_type}.enabled` / `.disabled`

---

## 关联表

### AgentTool（Agent 与 Tool 多对多）

| 字段 | 类型 | 说明 |
|------|------|------|
| agent_id | BIGINT FK | |
| tool_id | BIGINT FK | |

### AgentSkill（Agent 与 Skill 多对多）

| 字段 | 类型 | 说明 |
|------|------|------|
| agent_id | BIGINT FK | |
| skill_id | BIGINT FK | |

### PipelineSubAgent（Pipeline 与子 Agent 多对多）

| 字段 | 类型 | 说明 |
|------|------|------|
| pipeline_id | BIGINT FK | |
| agent_id | BIGINT FK | 必须是 SUB 类型 Agent |
| order_index | INT | 编排顺序（多 Agent 串行场景） |

### PipelineDetectionRule（Pipeline 与 DetectionRule 多对多）

| 字段 | 类型 | 说明 |
|------|------|------|
| pipeline_id | BIGINT FK | |
| rule_id | BIGINT FK | |

### SkillTool（Skill 依赖 Tool 多对多）

| 字段 | 类型 | 说明 |
|------|------|------|
| skill_id | BIGINT FK | |
| tool_id | BIGINT FK | |

---

## MarketplaceItem（商场视图，非独立表）

商场条目是对 Tool / Skill / Agent 的统一视图，通过 UNION 查询或应用层聚合实现：

| 字段 | 类型 | 说明 |
|------|------|------|
| item_type | ENUM('tool','skill','agent') | 条目类型 |
| item_id | BIGINT | 原始实体 ID |
| name | VARCHAR | 名称 |
| description | TEXT | 描述 |
| source_platform | VARCHAR | 来源平台 |
| tags | JSON | 标签 |
| version | VARCHAR | 版本 |
| enabled | BOOLEAN | 当前启用状态 |

---

## 数据库规范遵守

- 所有业务表包含 `id`（BIGINT AUTO_INCREMENT）、`created_at`、`updated_at`
- 字符集：utf8mb4，排序规则：utf8mb4_unicode_ci
- 敏感字段（`api_key`、`access_token`）加密存储，使用 AES-256-GCM，密钥从环境变量读取
- 所有结构变更通过 Alembic 迁移脚本管理
