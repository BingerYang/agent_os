# 快速启动指南：Agent 调度平台

**功能分支**: `001-agent-dispatch-platform` | **日期**: 2026-04-18

## 前置条件

| 工具 | 版本要求 | 检查命令 |
|------|---------|---------|
| Python | 3.12+ | `python --version` |
| uv | latest | `uv --version` |
| Node.js | 20+ | `node --version` |
| pnpm / npm | latest | `pnpm --version` |
| Git | 任意 | `git --version` |

> **开发阶段**：使用 SQLite，无需安装 MySQL。生产部署时替换 `DATABASE_URL`。

---

## 后端启动

```bash
# 1. 进入后端目录
cd backend

# 2. 创建并激活虚拟环境（uv 自动管理）
uv sync

# 3. 复制环境变量配置
cp .env.example .env

# 4. 编辑 .env（必填项）
# DATABASE_URL=sqlite+aiosqlite:///./dev.db
# SECRET_KEY=your-secret-key-here
# LLM_ENCRYPTION_KEY=your-aes-256-key-here

# 5. 运行数据库迁移
uv run alembic upgrade head

# 6. 启动开发服务器
uv run uvicorn src.main:app --reload --port 8000
```

服务启动后：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

---

## 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
pnpm install

# 3. 启动开发服务器（自动代理 /api 到后端 8000 端口）
pnpm dev
```

前端地址：http://localhost:5173

---

## 运行测试

```bash
# 后端单元测试
cd backend
uv run pytest tests/unit/ -v

# 后端集成测试（使用 SQLite，无需 MySQL）
uv run pytest tests/integration/ -v

# 后端全量测试（含覆盖率报告）
uv run pytest --cov=src --cov-report=term-missing

# 前端测试
cd frontend
pnpm test
```

---

## 生产环境（MySQL）

修改 `.env`：
```bash
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/agent_os?charset=utf8mb4
```

确保 MySQL 数据库已创建：
```sql
CREATE DATABASE agent_os CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

重新运行迁移：
```bash
uv run alembic upgrade head
```

---

## 快速验证（端到端）

1. 在模型配置页面配置一个 LLM 模型（填入有效 API Key）
2. 在 MCP 广场安装一个工具（如天气查询）
3. 在 Agent 管理页面创建一个 SINGLE 类型 Agent，关联该工具
4. 在 Pipeline 管理页面创建一个 SINGLE_AGENT 流水线，关联该 Agent
5. 调用 `POST /api/v1/query`：
   ```bash
   curl -X POST http://localhost:8000/api/v1/query \
     -H "Content-Type: application/json" \
     -d '{"query": "今天北京天气怎么样？", "pipeline_id": 1}'
   ```
6. 验证运行时 SSE 连接：
   ```bash
   curl -N http://localhost:8000/api/v1/events/stream
   ```
   在管理界面切换工具启用状态，观察 SSE 推送事件。

---

## 目录结构速查

```
agent_os/
├── backend/          # FastAPI 后端
├── frontend/         # Vue 3 前端
├── specs/            # 规格文档
│   └── 001-agent-dispatch-platform/
│       ├── plan.md
│       ├── research.md
│       ├── data-model.md
│       ├── quickstart.md  ← 本文件
│       ├── contracts/api.md
│       └── tasks.md      # 待生成
└── poc/              # 前端原型参考
```
