# 快速启动指南：管理端 / 运行时分离部署

**功能分支**: `003-backend-split-runtime` | **日期**: 2026-05-06

---

## 前置条件

- Python 3.12，uv 已安装
- MySQL 8.0+（生产）或 SQLite（开发）
- Redis 6.2+（支持 Redis Streams）
- MCP Server（若有工具依赖）

---

## 环境变量

`.env` 文件（管理端和运行时共用，通过环境变量区分角色）：

```env
# 数据库
DATABASE_URL=sqlite+aiosqlite:///./dev.db
# 生产: DATABASE_URL=mysql+aiomysql://user:pass@host:3306/agentdb?charset=utf8mb4

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_STREAM_KEY=agent:publish

# 安全
SECRET_KEY=your-secret-key-change-in-prod
LLM_ENCRYPTION_KEY=your-32-byte-base64-key

# 管理端配置
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# 运行时配置
RUNTIME_AGENT_LOAD_MODE=eager          # eager | lazy
RUNTIME_AGENT_POOL_MAX_SIZE=100        # 0 表示不限制
RUNTIME_MCP_CONNECT_ON_STARTUP=false   # lazy 模式下是否预热 MCP 连接
```

---

## 安装依赖

```bash
cd backend
uv sync
```

---

## 数据库迁移

```bash
cd backend
alembic upgrade head
```

---

## 单机开发模式（合并启动）

若开发时不需要分离，可使用原始 `main.py`（向后兼容，等同于管理端）：

```bash
cd backend
uv run uvicorn src.main:app --reload --port 8000
```

---

## 分离部署模式

### 启动管理端

```bash
cd backend
uv run uvicorn src.main_management:app --host 0.0.0.0 --port 8000
```

管理端提供：
- 全部 CRUD API（Agent、Tool、Skill、Pipeline 等）
- Agent 发布接口
- 前端所需的所有管理接口
- `/health` 端点

### 启动运行时

```bash
cd backend
uv run uvicorn src.main_runtime:app --host 0.0.0.0 --port 8001
```

运行时提供：
- `POST /api/v1/query`（流式和非流式）
- `/health` 端点
- 启动时自动加载已发布 Agent，订阅 Redis Stream

---

## 验证部署

### 检查管理端

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### 检查运行时

```bash
curl http://localhost:8001/health
# {"status": "ok", "agents_loaded": 5, "redis_subscribed": true}
```

### 发布 Agent（管理端操作）

```bash
curl -X PATCH http://localhost:8000/api/v1/agents/1/publish \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 验证运行时热加载（10 秒内）

```bash
# 发布后立即查询，验证使用最新配置
curl -X POST http://localhost:8001/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "你好", "pipeline_id": "pl_xxx", "stream": false}'
```

### 测试流式输出

```bash
curl -N -X POST http://localhost:8001/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "今天天气如何？", "pipeline_id": "pl_xxx", "stream": true}'
```

---

## 运行测试

```bash
cd backend

# 全量测试
uv run pytest

# 仅运行时相关测试
uv run pytest tests/integration/test_runtime_pool.py

# 覆盖率报告
uv run pytest --cov=src --cov-report=term-missing
```

---

## 生产部署示例（Docker）

```dockerfile
# 管理端
FROM python:3.12-slim
WORKDIR /app
COPY backend/ .
RUN pip install uv && uv sync --no-dev
CMD ["uv", "run", "uvicorn", "src.main_management:app", "--host", "0.0.0.0", "--port", "8000"]

# 运行时
FROM python:3.12-slim
WORKDIR /app
COPY backend/ .
RUN pip install uv && uv sync --no-dev
CMD ["uv", "run", "uvicorn", "src.main_runtime:app", "--host", "0.0.0.0", "--port", "8001"]
```

两个镜像使用相同代码库，通过 CMD 区分角色。
