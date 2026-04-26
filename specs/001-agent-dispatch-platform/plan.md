# Implementation Plan: Agent 调度平台

**Branch**: `001-agent-dispatch-platform` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)

---

> **文档定位说明**
>
> 本文档是原始功能规格（spec.md）的**实施规划**，分两部分：
> - **Part I**：初版实现规划（Phase 1–5，已基本实现，见 tasks.md）
> - **Part II**：模块细化补充规划（本次新增，针对 MCP/Skill/Agent 三个管理模块）
>
> Part II 不推翻原有设计，是对原规格 FR-011~FR-014（子系统管理）的详细落地设计。

---

## Technical Context

**Language/Version**: Python 3.12（后端）、Vue 3 + TypeScript（前端）
**Primary Dependencies**: FastAPI、SQLAlchemy（AsyncIO）、Pinia、Element Plus
**Storage**: SQLite（开发）/ MySQL 8.0+（生产），Alembic 迁移管理
**Testing**: pytest（后端）、Vitest（前端）
**Target Platform**: Web 应用（Linux 服务器部署）
**Project Type**: Web 应用（管理端 + 运行时 API）

---

## Constitution Check

| 原则 | 状态 | 说明 |
|------|------|------|
| I. RESTful 接口规范 | ✅ 合规 | 新增 `/api/v1/mcp-servers`，遵循名词复数 + 标准 HTTP 动词 |
| II. 技术栈合规性 | ✅ 合规 | 无新增技术栈，延续现有后端/前端选型 |
| III. 中文文档优先 | ✅ 合规 | 文档全程中文 |
| IV. 测试驱动开发 | ⚠️ 待执行 | MCPServer 服务层需先写测试 |
| V. 简单性优先 | ✅ 合规 | MCPServer 工具发现同步执行，不引入消息队列 |

---

## Part I：初版实现（已完成）

见 `tasks.md` Phase 1–5，核心交付：

- 基础设施（数据库、API 框架、统一响应）
- 单 Agent 流水线（意图识别→工具调用→前后置检测→输出）
- 多 Agent 编排（路由→子 Agent 调度→汇总）
- 管理端基础页面（LLM 模型、工具、Skill、Agent CRUD、流水线配置）

---

## Part II：模块细化补充规划

### 现状 Gap 分析

| 模块 | 现状 | 缺失 |
|------|------|------|
| MCP Server 管理 | **完全不存在** | MCPServer 模型、API、前端页面、Tool←Server 关联 |
| 工具库（MCPView） | 有工具 CRUD，但缺 Server 维度 | 按 Server 筛选；MCP 工具绑定 Server；auth 配置已加（本次 PR）|
| Skill 管理 | 基础 CRUD 可用 | 缺 `category`/`author` 字段；前端缺 `trigger_condition`/版本展示 |
| Agent 工作流 | 基础 CRUD 可用 | 缺意图识别配置、编排器配置、路由配置、子 Agent 管理、发布状态等生产级参数 |

---

### 补充模块 A：MCP Server 管理（新增）

**业务目标**：MCP 协议是 Server → Tools 的层级模型，一个 Server 可暴露多个 Tool。需统一管理 Server 的连接配置、认证方式，并自动发现其下工具写入工具库。

**导航**：侧边栏新增"MCP 服务"入口（路由 `/mcp-servers`），置于"工具库"之上。

**后端新增实体 MCPServer**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | |
| name | VARCHAR(128) UNIQUE | 唯一标识 |
| display_name | VARCHAR(256) | 展示名 |
| description | TEXT | 描述 |
| transport_type | ENUM(STDIO, HTTP_SSE) | 传输协议 |
| command | VARCHAR(512) | STDIO 启动命令（如 `npx -y @modelcontextprotocol/server-puppeteer`）|
| args | JSON | STDIO 参数列表 |
| env_vars | JSON（加密） | 环境变量，如 `{"PUPPETEER_API_KEY": "xxx"}` |
| endpoint_url | VARCHAR(512) | HTTP_SSE 服务地址 |
| auth_type | ENUM(NONE, API_KEY, BEARER_TOKEN, BASIC_AUTH) | 认证方式 |
| auth_config | JSON（加密） | 认证配置（同 Tool.auth_config 结构）|
| status | ENUM(UNKNOWN, CONNECTED, DISCONNECTED, ERROR) | 连接状态 |
| last_connected_at | DATETIME | 最后成功连接时间 |
| enabled | BOOLEAN | 启用状态 |
| created_at / updated_at | DATETIME | |

**后端新增 API**：

```
GET    /api/v1/mcp-servers                    # 列表（分页、keyword、enabled 筛选）
POST   /api/v1/mcp-servers                    # 创建
GET    /api/v1/mcp-servers/{id}               # 详情
PUT    /api/v1/mcp-servers/{id}               # 更新
DELETE /api/v1/mcp-servers/{id}               # 删除
PATCH  /api/v1/mcp-servers/{id}/toggle        # 启用/禁用
POST   /api/v1/mcp-servers/{id}/connect       # 测试连接（返回 status + latency_ms）
POST   /api/v1/mcp-servers/{id}/discover      # 发现工具（写入 Tool 表，返回新增工具数）
```

**Tool 模型新增字段**（补充现有 auth_type/auth_config）：

| 字段 | 类型 | 说明 |
|------|------|------|
| mcp_server_id | BIGINT FK（nullable） | 来源 MCP Server，手动工具为 NULL |
| mcp_tool_name | VARCHAR(128) | MCP 协议中的 tool name |

**前端新增 `MCPServersView.vue`**：

- 卡片/列表：Server 名称、传输类型、连接状态（带颜色指示）、工具数量
- 操作：新增 Server、编辑、删除、测试连接、发现工具（触发 discover 端点）
- 新增弹窗分两种模式：
  - STDIO 模式：command + args + env_vars（键值对编辑器）
  - HTTP_SSE 模式：endpoint_url + auth_type + auth_config

---

### 补充模块 B：工具库（MCPView 改造）

**业务目标**：改造现有"插件广场"MCPView，使其专注工具管理，增加 MCP Server 维度的筛选。

**前端 MCPView.vue 改动**：

- 页面标题改为"工具库"
- 筛选栏新增"来源 Server"下拉，可按 MCPServer 过滤工具
- 工具卡片：来自 MCP Server 的工具显示 Server 名称标签（不可编辑 endpoint，由 Server 统一管理）
- 手动添加工具（HTTP/BUILTIN）：保留现有流程，auth_type/auth_config 已本次 PR 加入

**后端 GET /api/v1/tools 新增查询参数**：

- `mcp_server_id: int | None` — 按来源 Server 筛选

---

### 补充模块 C：Skill 管理补充

**业务目标**：在现有基础 CRUD 上补充分类维度和完整配置展示，对齐 POC SkillPage 的运营体验。

**后端 Skill 模型新增字段**：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| category | VARCHAR(64) | 'general' | 分类（场景技能/基础技能/安全技能等）|
| author | VARCHAR(128) | '系统官方' | 来源/作者标识 |

**前端 SkillView.vue 补充**：

- 新增 category 筛选下拉
- 表格新增：版本、分类、作者列
- 新建/编辑弹窗新增：category 选择、trigger_condition 文本域（当前已有字段但前端没有暴露）、author 字段

---

### 补充模块 D：Agent 工作流编排补充

**业务目标**：AgentView.vue 当前仅有基础 CRUD，无法配置生产级 Agent 的核心参数（意图识别模型、编排策略、路由规则等）。需要完善为多 Tab 配置面板，对齐 POC WorkflowPage 的配置深度。

**后端 Agent 模型新增字段**：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| status | ENUM(draft, published) | draft | 发布状态 |
| temperature | FLOAT | 0.7 | LLM temperature |
| max_tokens | INT | 2048 | 最大输出 token |
| intent_recognition_enabled | BOOLEAN | FALSE | 是否启用意图识别（仅 SINGLE）|
| intent_model_id | BIGINT FK | NULL | 意图识别使用的 LLM |
| intent_confidence_threshold | FLOAT | 0.85 | 意图识别置信度阈值 |
| intent_system_prompt | TEXT | NULL | 意图识别系统提示词 |
| intent_entity_schema | JSON | NULL | 实体提取 schema：`[{name,type,required,desc}]` |
| routing_strategy | ENUM(smart, intent_rule) | smart | 路由策略（仅 ORCHESTRATOR）|
| routing_model_id | BIGINT FK | NULL | 路由使用的 LLM |
| routing_system_prompt | TEXT | NULL | 路由系统提示词 |
| routing_threshold | FLOAT | 0.8 | 路由置信度阈值 |
| routing_intent_rules | JSON | NULL | 意图路由规则：`[{intent,keywords[],targetAgents[],priority}]` |

**前端 AgentView.vue 改造**：

创建详情/编辑抽屉（`el-drawer`，宽 680px），分以下 Tab 配置：

| Tab | 适用类型 | 内容 |
|-----|---------|------|
| 基础配置 | 全部 | 名称、类型、描述、来源平台、access_url/token |
| LLM 模型 | 全部 | 选择 LLM 模型、system_prompt、temperature、max_tokens |
| 意图识别 | SINGLE | 开关、识别 LLM、置信度阈值、系统提示词、实体 Schema 编辑器 |
| 工具绑定 | SINGLE | 多选工具（支持按 MCP Server 筛选） |
| 技能绑定 | SINGLE | 多选 Skill |
| 编排器 | ORCHESTRATOR | 编排 LLM、system_prompt |
| 路由配置 | ORCHESTRATOR | 路由策略选择、路由 LLM、置信度阈值、系统提示词 |
| 路由规则 | ORCHESTRATOR（intent_rule 策略） | 意图规则列表：增删改（意图名、关键词、目标 Agent、优先级）|
| 子 Agent | ORCHESTRATOR | 绑定/移除子 Agent，设置调用顺序 |
| 检测规则 | 全部 | 绑定前置/后置检测规则 |

列表页增加"发布/下架"快捷操作（映射 status 字段）。

---

## Project Structure（增量）

```text
backend/
├── src/
│   ├── models/
│   │   ├── mcp_server.py          # NEW
│   │   ├── tool.py                # 新增 mcp_server_id, mcp_tool_name（+ 已有 auth_type/auth_config）
│   │   ├── skill.py               # 新增 category, author
│   │   └── agent.py               # 新增 status, temperature, max_tokens, intent_*, routing_*
│   ├── services/
│   │   └── mcp_server_service.py  # NEW：CRUD + 连接检测 + 工具发现
│   └── api/v1/
│       ├── mcp_servers.py         # NEW
│       ├── tools.py               # 新增 mcp_server_id 查询参数
│       ├── skills.py              # 新增 category/author 字段支持
│       ├── agents.py              # 新增完整配置字段
│       └── router.py              # 注册 mcp_servers 路由

frontend/
├── src/
│   ├── views/
│   │   ├── MCPServersView.vue     # NEW
│   │   ├── MCPView.vue            # 改造：工具库，增 Server 筛选
│   │   ├── SkillView.vue          # 补充：category/version/author/trigger_condition
│   │   └── AgentView.vue          # 重构：多 Tab 抽屉配置
│   ├── stores/
│   │   └── mcpServers.ts          # NEW
│   └── router/index.ts            # 新增 /mcp-servers 路由
```

---

## Complexity Tracking

| 复杂度引入 | 理由 | 拒绝的更简方案 |
|-----------|------|---------------|
| MCPServer 独立实体 + 工具发现 | MCP 协议天然是 Server→Tools 层级；扁平存储无法统一管理认证和工具 | 每工具单存 server_url：认证管理爆炸，无法做 Server 级启停 |
| Agent 多 Tab 配置面板 | 生产级 Agent 必须支持意图识别和路由参数配置，POC 已验证这是核心运营需求 | 仅 name+system_prompt：无法驱动真实 Agent 运行 |

---

## Codex Execute Command（增量任务参考）

| Task ID | 文件 | 操作说明 |
|---------|------|---------|
| S-01 | `backend/src/models/mcp_server.py` | 创建 MCPServer 模型（含上述全部字段）|
| S-02 | `backend/src/models/tool.py` | 新增 mcp_server_id FK + mcp_tool_name 字段 |
| S-03 | `backend/src/models/skill.py` | 新增 category + author 字段 |
| S-04 | `backend/src/models/agent.py` | 新增 status、LLM 参数、intent_*、routing_* 字段 |
| S-05 | `backend/alembic/versions/` | 生成 Alembic 迁移文件覆盖全部 DDL 变更 |
| S-06 | `backend/src/services/mcp_server_service.py` | CRUD + connect（httpx 检测）+ discover（解析工具写入 Tool 表）|
| S-07 | `backend/src/api/v1/mcp_servers.py` | 完整 REST API（含 connect/discover 端点）|
| S-08 | `backend/src/api/v1/router.py` | 注册 mcp_servers 路由 |
| S-09 | `backend/src/api/v1/tools.py` | 新增 mcp_server_id 查询参数 |
| S-10 | `backend/src/api/v1/skills.py` | 支持 category/author 字段读写 |
| S-11 | `backend/src/api/v1/agents.py` | 扩展 AgentCreate/AgentUpdate 含所有新字段 |
| S-12 | `frontend/src/stores/mcpServers.ts` | MCPServer Pinia store（CRUD + connect + discover）|
| S-13 | `frontend/src/views/MCPServersView.vue` | MCP Server 管理页 |
| S-14 | `frontend/src/views/MCPView.vue` | 改造：工具库，增 Server 筛选 |
| S-15 | `frontend/src/views/SkillView.vue` | 补充 category/trigger_condition/version/author |
| S-16 | `frontend/src/views/AgentView.vue` | 重构为多 Tab 抽屉配置 |
| S-17 | `frontend/src/router/index.ts` | 新增 /mcp-servers 路由 + 侧边栏入口 |
