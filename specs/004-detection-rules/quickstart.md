# Quickstart: Agent 检测规则引擎

**Feature**: 004-detection-rules
**Date**: 2026-05-14

本文档是开发完成后的验证手册，按顺序执行可验证全部核心功能。

---

## 前置条件

```bash
# 运行数据库迁移
cd backend
uv run alembic upgrade head

# 启动管理端
uv run python -m src.main_management

# 启动运行时
uv run python -m src.main_runtime
```

---

## Step 1：创建策略规则（全局模板）

```bash
# 创建"限流防刷"策略
curl -X POST http://localhost:8000/api/v1/detection-rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "全局限流-100次/分钟",
    "stage": "PRE",
    "strategy_type": "rate_limit",
    "rule_type": "keyword",
    "action_type": "block",
    "rule_content": {"window_seconds": 60, "max_requests": 100, "key_by": "user"},
    "reject_message": "请求频率超限，请稍后重试",
    "priority": 10
  }'

# 创建"违规内容拦截"策略
curl -X POST http://localhost:8000/api/v1/detection-rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "违规内容拦截-默认",
    "stage": "PRE",
    "strategy_type": "content_filter",
    "rule_type": "keyword",
    "action_type": "block",
    "rule_content": {
      "sub_types": ["political", "pornography", "violence", "attack"],
      "keywords": ["测试违禁词"],
      "patterns": []
    },
    "reject_message": "您的请求包含违规内容，已被拦截",
    "priority": 20
  }'
```

**预期**：两条规则创建成功，返回 `code: 0`。

---

## Step 2：将策略绑定到 Agent（per-agent 配置）

```bash
# 假设 agent_id = 1
# 绑定限流策略，per-agent 覆盖阈值为 50 次/分钟
curl -X POST http://localhost:8000/api/v1/agents/1/detection-bindings \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": 1,
    "enabled": true,
    "config_override": {"max_requests": 50},
    "action_override": null
  }'

# 查看 Agent 策略绑定概览
curl http://localhost:8000/api/v1/agents/1/detection-bindings/summary
```

**预期**：
- 绑定成功，`effective_config.max_requests = 50`（覆盖全局 100）
- summary 接口中 `pre_checks` 列表包含 `rate_limit` 策略，`enabled: true`

---

## Step 3：验证前置策略执行

```bash
# 发起 Agent 查询（假设 agent_id=1 的调用接口为 /api/v1/query/{agent_id}）
curl -X POST http://localhost:8000/api/v1/query/1 \
  -H "Content-Type: application/json" \
  -d '{"query": "测试违禁词 请帮我查询订单"}'
```

**预期**：返回 HTTP 200，`code` 非 0，`message` 包含"违规内容"拦截提示。

```bash
# 发起正常查询（不含违禁词）
curl -X POST http://localhost:8000/api/v1/query/1 \
  -H "Content-Type: application/json" \
  -d '{"query": "帮我查询订单号 12345"}'
```

**预期**：策略通过，Agent 正常响应。

---

## Step 4：验证后置策略（PII 防泄密）

```bash
# 创建后置 PII 防泄密策略
curl -X POST http://localhost:8000/api/v1/detection-rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "后置PII防泄密",
    "stage": "POST",
    "strategy_type": "privacy_leak",
    "rule_type": "keyword",
    "action_type": "rewrite",
    "rule_content": {
      "pii_types": ["phone", "idcard", "email"],
      "mask_pattern": "***"
    },
    "priority": 10
  }'

# 绑定到 Agent 1
curl -X POST http://localhost:8000/api/v1/agents/1/detection-bindings \
  -H "Content-Type: application/json" \
  -d '{"rule_id": 3, "enabled": true}'
```

**预期**：Agent 响应中包含手机号时，返回给调用方的内容中手机号被替换为 `***`。

---

## Step 5：查看审计日志

```bash
# 查看所有检测事件
curl "http://localhost:8000/api/v1/detection-events?agent_id=1&page=1&page_size=10"
```

**预期**：Step 3 的违禁词拦截事件出现在日志中，包含 `strategy_type: content_filter`、`action_taken: block`。

---

## Step 6：Web 端验证

1. 打开 `http://localhost:5173`
2. 进入"检测规则"页面：验证策略列表显示 `strategy_type`、`action_type` 列
3. 进入某 Agent 详情页，点击"检测策略"Tab：验证前置/后置策略绑定列表显示
4. 修改某 Agent 的策略参数并保存：验证"配置变更审计"记录出现
5. 进入"审计日志"Tab：验证 Step 3、Step 4 的命中记录可查询和筛选

---

## 回归验证

```bash
# 确保现有 pipeline 检测规则未受影响
cd backend && uv run pytest tests/ -k "detection" -v
```

**预期**：全部通过，覆盖率 ≥ 80%。
