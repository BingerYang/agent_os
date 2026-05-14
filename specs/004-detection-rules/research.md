# Research: Agent 检测规则引擎

**Feature**: 004-detection-rules
**Date**: 2026-05-14

---

## 0. LangChain 1.0+ Middleware 评估（已通过实测验证）

### 包版本基准（项目实际安装）

| 包 | 项目安装版本 | PyPI 最新版（2026-05-14） |
|----|------------|--------------------------|
| `langchain` | **1.2.15** | 1.2.15（已是最新）|
| `deepagents` | **0.5.3** | 0.6.1（可升级，API 兼容）|

**参考链接**：
- deepagents PyPI: [pypi.org/project/deepagents/](https://pypi.org/project/deepagents/)
- deepagents GitHub: [github.com/langchain-ai/deepagents](https://github.com/langchain-ai/deepagents)
- create_deep_agent API: [reference.langchain.com/python/deepagents/graph/create_deep_agent](https://reference.langchain.com/python/deepagents/graph/create_deep_agent)
- HumanInTheLoopMiddleware: [reference.langchain.com/python/langchain/agents/middleware/human_in_the_loop/HumanInTheLoopMiddleware](https://reference.langchain.com/python/langchain/agents/middleware/human_in_the_loop/HumanInTheLoopMiddleware)
- Middleware 文档: [docs.langchain.com/oss/python/langchain/middleware/overview](https://docs.langchain.com/oss/python/langchain/middleware/overview)
- HITL Blog: [blog.langchain.com/agent-middleware/](https://blog.langchain.com/agent-middleware/)

---

### HumanInTheLoopMiddleware — 已确认真实存在 ✅

**导入路径（实测）**：
```python
from langchain.agents.middleware import HumanInTheLoopMiddleware
```

**构造函数签名（`inspect.signature` 实测，langchain 1.2.15）**：
```python
HumanInTheLoopMiddleware(
    interrupt_on: dict[str, bool | InterruptOnConfig],
    *,
    description_prefix: str = 'Tool execution requires approval'
) -> None
```

**功能**：在 Agent 调用工具前暂停执行，等待人工决策（approve / edit / reject），
需要 `checkpointer` 持久化中断状态，通过 `thread_id` 标识对话线程并在审批后恢复。

---

### create_deep_agent 完整参数签名（实测 deepagents 0.5.3）

```python
create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware] = (),          # ← 接受 HumanInTheLoopMiddleware 等
    subagents: Sequence[SubAgent | ...] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    permissions: list[FilesystemPermission] | None = None,
    response_format: ... = None,
    context_schema: type | None = None,
    checkpointer: None | bool | BaseCheckpointSaver = None,  # ← HITL 必需
    store: BaseStore | None = None,
    backend: BackendProtocol | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,  # ← HITL 快捷配置
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache | None = None,
) -> CompiledStateGraph
```

---

### 关键架构区分：Tool-level 工具审批 vs Response-level 响应审批

`HumanInTheLoopMiddleware` 在 Agent 调用工具**之前**中断，适用于工具级别审批。
A-03 要求在 Agent 产生**最终响应之后**、返回给用户**之前**审批，属于响应级别。

| 审批类型 | 触发时机 | 推荐方案 |
|----------|----------|---------|
| **工具调用级别** | AIMessage 生成工具调用后，工具执行前 | `HumanInTheLoopMiddleware` + `checkpointer` |
| **响应输出级别（A-03）** | Agent 产生最终 answer 后，返回调用方前 | 外部异步队列（DetectionEvent 表）|

---

### Decision: P-01～P-08、A-01～A-02 继续使用外层包裹 ✅

| 方案 | 结论 |
|------|------|
| LangChain Callbacks | ❌ 仅观测，无法阻断执行 |
| `HumanInTheLoopMiddleware` | ❌ 工具调用级别中断，不适合请求入口拦截（P-01 限流等需在 LLM 调用前拦截）|
| **外层包裹（query_service.py）** | ✅ 在 LLM 调用前拦截，完整控制执行流，符合 YAGNI |

---

### Decision: A-03 人机审批使用外部异步队列（响应级），不使用 HumanInTheLoopMiddleware ✅

**理由**：`HumanInTheLoopMiddleware` 是工具级审批，A-03 是响应级审批，语义不匹配。

| 方案 | 评估 |
|------|------|
| `HumanInTheLoopMiddleware` + checkpointer | ⚠️ 解决工具调用审批，不解决响应审批；且需为每个 Agent 配置 checkpointer，改动面广 |
| **外部异步队列（DetectionEvent 表）** | ✅ A-03 命中 → `DetectionEvent(ESCALATED)` → 返回 `pending_approval` → 审批员 Web 端 → `asyncio.Event` 恢复 |

---

### 扩展：HumanInTheLoopMiddleware 的推荐使用场景（超出本次范围，记录备用）

虽然 A-03 不使用 `HumanInTheLoopMiddleware`，但它可增强工具级别的高风险操作审批
（适合未来扩展 P-07 RBAC 或 P-08 业务硬规则中的危险操作防护）：

```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_deep_agent(
    model=llm,
    tools=[high_risk_tool],
    middleware=[
        HumanInTheLoopMiddleware(interrupt_on={
            "delete_record": True,
            "send_email": {"allowed_decisions": ["approve", "reject"]},
        })
    ],
    checkpointer=True,  # 生产环境建议 AsyncRedisSaver 或 AsyncSqliteSaver
)
```

现有执行链路（保持不变）：
```
query_service.py:
  run_pre_detection(pre_rules, query)    ← 外层包裹，LangGraph 外
  ↓
  node.execute(agent_ctx)                ← 内部：deepagents CompiledStateGraph.ainvoke()
  ↓
  run_post_detection(post_rules, answer) ← 外层包裹，LangGraph 外
```

---

## 1. 现有代码库状态分析

### Decision: 增量扩展而非重写

**Rationale**: 后端已有可运行的 `DetectionRule` 模型、`DetectionService`、`detection.py`
执行引擎、`/api/v1/detection-rules` 路由。本次工作在现有基础上**增量扩展**，
而非推倒重建，最大化复用已有逻辑。

**Alternatives considered**:
- 全量重建独立检测引擎（开发成本高，风险大，现有代码已在 pipeline 中被使用）
- 不动后端只改前端（满足不了策略类型细化和 per-agent 配置要求）

**现有可复用组件**：
| 文件 | 状态 | 本次扩展点 |
|------|------|-----------|
| `models/detection_rule.py` | ✅ 可用 | 新增 `strategy_type`、`action_type` 字段 |
| `services/detection_service.py` | ✅ 可用 | 新增 `get_rules_for_agent` 方法 |
| `agents/detection.py` | ✅ 可用 | 新增 P-01/P-08 各策略执行逻辑 |
| `api/v1/detection_rules.py` | ✅ 可用 | 新增 Agent 绑定 / 事件日志端点 |
| `frontend/DetectionRulesPage.tsx` | ✅ 可用 | 改造为策略模板管理视图 |
| `frontend/AgentPage.tsx` | ✅ 可用 | 新增"检测策略"Tab |

---

## 2. 策略执行机制设计

### Decision: 每种策略实现独立执行函数，通过 strategy_type dispatch

**Rationale**: 11 种策略的 `rule_content` 结构和执行逻辑差异较大（限流需要计数器，
PII 脱敏需要 NER，RBAC 需要权限矩阵），统一到同一函数会导致 if/else 膨胀。
采用策略函数注册表（`STRATEGY_REGISTRY: dict[StrategyType, Callable]`）实现 dispatch。

**Alternatives considered**:
- 全部走 LLM judge（灵活但延迟高且成本大，限流等规则型策略不适合）
- 继承体系（Python ABC，复杂度高，YAGNI）

### 各策略执行方案

| 策略 | 执行方式 | rule_content 主要字段 |
|------|----------|----------------------|
| P-01 限流防刷 | Redis 滑动窗口计数 | `window_seconds`, `max_requests`, `key_by` (user/ip/agent) |
| P-02 身份校验 | 复用现有鉴权中间件 | `require_token_types` (list), `check_expiry` |
| P-03 违规内容 | 关键词 + 可选 LLM judge | `sub_types` (list), `keywords`, `patterns`, `llm_model_id` |
| P-04 Prompt 注入 | 正则模式 + 可选 LLM | `patterns`, `injection_keywords`, `llm_model_id` |
| P-05 PII 脱敏 | 正则识别 → 替换 | `pii_types` (phone/idcard/email/bankcard/name), `mask_pattern` |
| P-06 意图合规 | LLM judge | `allowed_intents`, `llm_model_id`, `system_prompt` |
| P-07 RBAC | 角色权限矩阵查询 | `required_roles`, `required_permissions` |
| P-08 业务硬规则 | 内置规则类型组合 | `rules`: [{type, params}]，type ∈ {time, geo, ip_blacklist, user_blacklist} |
| A-01 后置隐私 | 正则识别 → 替换/拦截 | 同 P-05，但作用于输出 |
| A-02 业务结果校验 | 规则校验（格式/字段/值域） | `schema_checks`, `field_rules`, `retry_count` |
| A-03 人机审批 | 写入 ReviewQueue，阻塞等待 | `timeout_seconds`, `fallback_action`, `approver_roles` |

---

## 3. per-Agent 配置覆盖模型

### Decision: `AgentDetectionBinding` 表 + JSON config_override

**Rationale**: 全局 `DetectionRule` 存储策略模板和默认配置；`AgentDetectionBinding` 存储
per-agent 的启用状态和配置覆盖（JSON Merge Patch 语义）。运行时合并：
`merged = {**rule.rule_content, **binding.config_override}`。
这种设计复用全局规则，同时支持 agent 级别的差异化配置，符合"全局默认 + per-Agent 覆盖"要求。

**Alternatives considered**:
- 复制规则到每个 agent（数据冗余，同步困难）
- 在 `AgentPage` 存 JSON（规则管理散乱，无独立生命周期）

---

## 4. 处置动作执行

### Decision: `ActionType` 枚举 + 每种 action 独立执行分支

**Rationale**: 8 种处置动作（block/rewrite/log_review/retry/log_only/degrade/escalate/alert）
的后续行为差异大。`action_type` 存储在 `DetectionRule` 上作为默认，
`config_override` 可在 agent 级别覆盖 `action_type`。

**执行语义**：
- `block`: 抛出 `PreCheckRejected` / `PostCheckRejected`（现有行为）
- `rewrite`: 返回修改后的 text，而非抛出异常（detection 函数需返回 `(hit: bool, rewritten_text: str | None)`）
- `log_review`: 写入 `DetectionEvent`（status=PENDING_REVIEW），继续流转
- `retry`: 返回 `RetrySignal`，调用方重试（最多 `retry_count` 次）
- `log_only`: 写入 `DetectionEvent`（status=LOGGED），继续流转
- `degrade`: 返回 `DegradeSignal`，调用方以受限模式执行
- `escalate`: 写入 ReviewQueue（status=ESCALATED），阻塞等待
- `alert`: 异步发送告警事件到 `event_bus`，继续流转

---

## 5. 审计日志架构

### Decision: `DetectionEvent` 表（兼做 Review Queue）

**Rationale**: `log_review`、`log_only`、`escalate` 三种 action 都需要持久化事件记录。
用统一的 `DetectionEvent` 表，通过 `status` 字段区分状态：
`LOGGED` / `PENDING_REVIEW` / `REVIEWED` / `ESCALATED` / `RESOLVED`。
避免建多张表增加复杂度。

**Review Queue = DetectionEvent WHERE action IN (log_review, escalate) AND status IN (PENDING_REVIEW, ESCALATED)**

---

## 6. 数据库迁移策略

### Decision: Alembic 增量迁移，不修改现有表的现有列

**Rationale**: 
- `detection_rules` 表：**新增列**（`strategy_type`, `action_type`, `max_retry_count`）
- **新增表**：`agent_detection_bindings`、`detection_events`、`policy_config_audits`
- 保留 `pipeline_detection_rules` 不动（向后兼容）

**Alembic 操作**：
1. `ALTER TABLE detection_rules ADD COLUMN strategy_type VARCHAR(32) DEFAULT 'content_filter'`
2. `ALTER TABLE detection_rules ADD COLUMN action_type VARCHAR(32) DEFAULT 'block'`
3. `ALTER TABLE detection_rules ADD COLUMN max_retry_count INT DEFAULT 3`
4. `CREATE TABLE agent_detection_bindings ...`
5. `CREATE TABLE detection_events ...`
6. `CREATE TABLE policy_config_audits ...`

---

## 7. 前端架构决策

### Decision: 双入口设计（全局规则管理 + Agent 策略绑定 Tab）

**Rationale**: 
- **全局规则管理**（现有 `DetectionRulesPage.tsx` 改造）：管理策略模板定义和全局默认配置，
  新增 `strategy_type` 选择器和对应配置表单
- **Agent 策略 Tab**（`AgentPage.tsx` 新增 Tab）：管理当前 Agent 的策略绑定和 per-agent 覆盖
- 审计日志：在 `DetectionRulesPage` 新增审计日志 Tab，或独立路由页

**Alternatives considered**:
- 仅在 Agent 详情页配置所有内容（全局视角缺失，无法统一管理跨 Agent 的策略）
