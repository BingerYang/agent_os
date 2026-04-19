# Agent OS — 可配置可扩展智能体编排平台

一套统一入口的 Agent 调度平台，支持单 Agent 工具调度与多 Agent 协作编排，运营人员可通过商场式 UI 插拔 MCP 工具、技能和子 Agent，配置变更通过 SSE 实时推送至运行时，无需重启。

---

## 功能概览

| 用户故事 | 核心能力 |
|---------|---------|
| US1 单 Agent 流水线 | 意图识别 → 工具调用 → 前/后置检测 → 自然语言回复 |
| US2 多 Agent 编排 | LangGraph 路由 → 并行/串行子 Agent → 聚合 → 超时降级 |
| US3 商场式管理 | Tool / Skill / Agent 安装卸载，无需重启立即生效 |
| US4 配置实时同步 | SSE 事件总线推送，config_cache 解耦 DB 直连 |

---

## 技术栈

**后端**

- Python 3.12 / FastAPI / SQLAlchemy 2.x async
- LangChain ≥ 1.0 · LangGraph ≥ 1.0 · deepagents
- Alembic 迁移 · aiosqlite（开发）/ aiomysql（生产）
- AES-256-GCM 加密存储 LLM API Key
- sse-starlette SSE 推送

**前端**

- Vue 3 + TypeScript / Vite / Element Plus
- Pinia 状态管理 · Vue Router 4
- Vitest 组件测试

**质量**

- pytest（单元 + 集成 + 契约）· mypy strict
- ruff format + check · TDD（先写失败测试再实现）

---

## 目录结构

```
agent_os/
├── backend/
│   ├── src/
│   │   ├── api/v1/          # 路由层（tools / skills / agents / pipelines /
│   │   │                    #         detection_rules / marketplace / query / events）
│   │   ├── agents/          # detection · intent_router · single_agent · multi_agent
│   │   ├── models/          # SQLAlchemy ORM
│   │   ├── services/        # 业务逻辑（含 event_bus · config_cache）
│   │   └── core/            # config · database · exceptions · schemas · middleware
│   ├── tests/
│   │   ├── unit/            # 纯逻辑单元测试（mock LLM）
│   │   ├── integration/     # 端到端 API 集成测试
│   │   └── contract/        # JSON Schema 契约测试
│   ├── alembic/             # 数据库迁移
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── views/           # ModelView · AgentView · WorkflowView · MCPView ·
│   │   │                    #   SkillView · PipelineView
│   │   ├── stores/          # Pinia（agent · marketplace）
│   │   ├── components/      # StatusTag · SearchBar · MarketplaceCard
│   │   ├── api/             # Axios 实例（ApiResponse 拆包）
│   │   └── router/          # 路由 + 未配置模型导航守卫
│   └── package.json
└── specs/001-agent-dispatch-platform/   # 规格 / 设计 / 任务文档
```

---

## 快速启动

### 后端

```bash
cd backend

# 安装依赖（uv 自动创建虚拟环境）
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env，填写：
#   DATABASE_URL=sqlite+aiosqlite:///./dev.db
#   SECRET_KEY=<随机字符串>
#   LLM_ENCRYPTION_KEY=<32字节 base64，可用以下命令生成>
#   python3 -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"

# 数据库迁移
uv run alembic upgrade head

# 启动开发服务器
uv run uvicorn src.main:app --reload --port 8000
```

- API 文档：http://localhost:8000/docs
- 健康检查：`curl http://localhost:8000/health`

### 前端

```bash
cd frontend
npm/pnpm install
npm/pnpm run dev        # http://localhost:5173
```

---

## 运行测试

```bash
cd backend

# 全量测试
uv run pytest tests/ -v

# 单元测试（无 DB 依赖，速度最快）
uv run pytest tests/unit/ -v

# 含覆盖率
uv run pytest --cov=src --cov-report=term-missing

# 类型检查
uv run mypy src/ --ignore-missing-imports
```

---

## 核心 API

### 查询入口

```bash
# 同步查询
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "今天北京天气怎么样？", "pipeline_id": 1}'

# 流式查询（SSE）
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "...", "pipeline_id": 1, "stream": true}'
```

### 配置变更实时推送

```bash
# 订阅事件流（保持连接）
curl -N http://localhost:8000/api/v1/events/stream

# 获取全量配置快照
curl http://localhost:8000/api/v1/config/snapshot
```

### 商场管理

```bash
# 安装工具
curl -X POST http://localhost:8000/api/v1/marketplace/tool/1/install

# 卸载技能
curl -X DELETE http://localhost:8000/api/v1/marketplace/skill/2/install

# 注册第三方 Agent
curl -X POST http://localhost:8000/api/v1/marketplace/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "外部Agent", "access_url": "https://...", "access_token": "...", "description": "..."}'
```

---

## 端到端验证流程

1. 在 **模型配置**（`/model`）页面添加 LLM 模型，填入有效 API Key
2. 在 **MCP 广场**（`/mcp`）安装一个工具
3. 在 **Agent 管理**（`/agent`）创建 SINGLE 类型 Agent，关联该工具
4. 创建 SINGLE_AGENT Pipeline，关联该 Agent
5. 调用 `POST /api/v1/query` 验证完整链路

---

## 生产部署（MySQL）

```bash
# .env
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/agent_os?charset=utf8mb4

# 建库
mysql -e "CREATE DATABASE agent_os CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 迁移
uv run alembic upgrade head
```

---

## 错误码说明

| code | 含义 |
|------|------|
| 0 | 成功 |
| 40301 | 前置检测拦截（违禁内容） |
| 40302 | 后置检测拦截（输出违规） |
| 40401 | 资源不存在 |
| 40901 | 资源冲突（名称重复等） |
| 42201 | 参数校验失败 |
| 50001 | 服务器内部错误 |

---

## 性能基准

| 指标 | 目标 | 实测 |
|------|------|------|
| 事件传播延迟 P99 | ≤ 10s | ~0.1ms |
| 单工具查询 P95 | ≤ 3s | 取决于 LLM 响应速度 |
