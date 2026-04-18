# 研究报告：Agent 调度平台技术选型

**功能分支**: `001-agent-dispatch-platform` | **日期**: 2026-04-18（基于实际参考资料更新）

---

## 1. DeepAgents 框架（准确信息）

**来源**: [GitHub - langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) | [官方文档](https://docs.langchain.com/oss/python/deepagents/overview) | [PyPI](https://pypi.org/project/deepagents/)

**决策**: DeepAgents 是 LangChain 官方团队（langchain-ai）发布的高级 Agent 框架，直接构建于 LangGraph 之上，作为"一键创建具备完整能力 Agent"的最高层抽象。MIT 开源许可。

**核心概念**:
- DeepAgents 是对 Claude Code、Manus 等复杂 Agent 系统的通用化实现
- 核心函数 `create_deep_agent(model, tools, system_prompt)` 返回一个 `CompiledStateGraph` 实例（LangGraph 编译态）
- 开箱即用能力：任务规划工具、文件系统、子 Agent 生成、上下文记忆压缩

**Middleware 栈**（DeepAgents 内置）:
| Middleware | 作用 |
|-----------|------|
| `MemoryMiddleware` | 从 `AGENTS.md` 文件加载上下文到系统 prompt |
| `SkillsMiddleware` | 动态加载自定义 Python 脚本作为工具 |
| `FilesystemMiddleware` | 文件操作：ls/read/write/edit/glob/grep |
| `SubAgentMiddleware` | 生成具有独立上下文窗口的子 Agent |
| `SummarizationMiddleware` | Token 超限时自动压缩对话历史 |
| `PatchToolCallsMiddleware` | 修正 LLM 工具调用参数格式错误 |

**安装方式**:
```bash
uv add deepagents
```

**最小用法**:
```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=model,           # 任意支持 tool calling 的 LLM
    tools=[web_search],    # 自定义工具列表
    system_prompt="...",
)
# 返回 CompiledStateGraph，可直接 invoke/stream
result = await agent.ainvoke({"messages": [HumanMessage(content=query)]})
```

**与本项目的结合方式**:
- **单 Agent 流水线**：`create_deep_agent` 配置工具列表 → 直接处理复杂多步骤任务，内置 SubAgentMiddleware 支持子任务分解
- **多 Agent 编排**：多个 `create_deep_agent` 实例作为 LangGraph `StateGraph` 的节点，由主编排节点路由调用
- **前后置检测**：通过 LangChain 1.0 middleware 注入检测逻辑（见第 2 节）

**选型对比**:
- 直接用 LangChain `create_agent`：更轻量，适合简单工具调用；缺少规划/子 Agent/记忆管理
- 使用 DeepAgents：开箱即用复杂 Agent 能力，适合本项目"支持复杂多工具/多 Agent 编排"的需求
- **结论**：以 DeepAgents 作为主 Agent 执行引擎，LangGraph 作为多 Agent 编排底层

---

## 2. LangChain ≥ 1.0.0 架构变化（2025-10-22 正式发布）

**来源**: [LangChain & LangGraph 1.0 公告](https://blog.langchain.com/langchain-langgraph-1dot0/) | [LangGraph 1.0 GA](https://changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available)

### 核心架构反转（CRITICAL）

> **LangGraph 是底层运行时，LangChain 是构建于其上的高级 API** —— 这与 1.0 之前的认知完全相反。

| 层级 | 组件 | 说明 |
|------|------|------|
| 最高层 | DeepAgents | 复杂 Agent 的一体化 harness（本项目主要使用） |
| 高层 | LangChain 1.0 | `create_agent` API + Middleware 体系 |
| 底层运行时 | LangGraph 1.0 | 状态图、持久化、流式、人机循环 |

### 废弃的旧 API（禁止在新代码中使用）

| 废弃项 | 替代方案 |
|--------|---------|
| `AgentExecutor` | `create_agent`（LangChain 1.0）或 `create_deep_agent`（DeepAgents） |
| `create_react_agent`（from langgraph.prebuilt） | `create_agent`（from langchain.agents） |
| LCEL 管道语法（`prompt \| llm \| parser`） | Middleware + `create_agent` |
| `langgraph.prebuilt` 模块 | `langchain.agents`（功能已迁移） |

### 新核心 API

**`create_agent`（LangChain 1.0 标准 Agent 创建方式）**:
```python
from langchain.agents import create_agent

agent = create_agent(
    model=llm,
    tools=tools,
    middleware=[pre_check_middleware, post_check_middleware],
)
```

**Middleware（关键新概念）**:
- 在 Agent 循环中注入预处理/后验证逻辑，无需额外 LangGraph 节点
- 可在 LLM 调用前/后、工具调用前/后注入逻辑
- **直接映射本项目的前置/后置检测需求**（FR-003/FR-004）

```python
class PreDetectionMiddleware(BaseMiddleware):
    async def on_messages(self, messages, config):
        # 检测用户输入
        if await detection_service.check_pre(messages[-1].content):
            raise PreCheckRejected("内容违规")
        return messages

class PostDetectionMiddleware(BaseMiddleware):
    async def on_llm_end(self, output, config):
        # 检测 LLM 输出
        if await detection_service.check_post(output.content):
            raise PostCheckRejected("输出违规")
        return output
```

### LangGraph 1.0 生产级特性

- **持久化状态**：Agent 执行状态自动持久化，服务重启后从断点恢复
- **内置 Checkpointing**：多会话、多天跨会话工作流支持
- **人机循环（Human-in-the-loop）**：一等公民 API，可在任意节点暂停等待人工审批
- **稳定性承诺**：1.0 → 2.0 无破坏性变更

### 依赖版本更新

```toml
# pyproject.toml
langchain = ">=1.0.0"
langgraph = ">=1.0.0"
deepagents = ">=0.1.0"   # 具体版本以 PyPI 为准
```

---

## 3. 修订后的 Agent 架构（基于准确信息）

### 单 Agent 流水线

```
用户查询
  → PreDetectionMiddleware（LangChain middleware）
  → create_deep_agent（DeepAgents）
      ├── 意图识别 + 工具选择（LLM + planning tool）
      ├── 工具调用循环（MCP/HTTP 工具）
      └── 结果汇总（LLM）
  → PostDetectionMiddleware（LangChain middleware）
  → 返回用户
```

### 多 Agent 流水线

```
用户查询
  → PreDetectionMiddleware
  → 路由节点（LLM 判断目标子 Agent）
      ├── 置信度 ≥ 阈值 → 单子 Agent（create_deep_agent 实例）
      └── 置信度 < 阈值 → 多子 Agent（LangGraph StateGraph 并行/串行节点）
  → 结果聚合节点
  → PostDetectionMiddleware
  → 返回用户
```

### 架构层次映射

| 本项目模块 | 使用的框架组件 |
|-----------|-------------|
| `agents/single_agent.py` | `deepagents.create_deep_agent` |
| `agents/multi_agent.py` | `langgraph.StateGraph` + 多个 `create_deep_agent` 节点 |
| `agents/intent_router.py` | LangChain 1.0 `create_agent` + 路由 prompt |
| `agents/detection.py` | LangChain 1.0 `BaseMiddleware` 子类 |

---

## 4. 运行时/管理端事件通知机制

**决策**: V1 使用 SSE（Server-Sent Events）+ 内存事件总线；架构预留切换至 Redis Pub/Sub
**理由**:
- SSE 是 HTTP 原生协议，无需额外基础设施（YAGNI 原则）
- FastAPI 通过 `sse-starlette` 库原生支持 SSE 异步流
- 内存总线：`asyncio.Queue` 广播模式，运行时订阅方持有 Queue 引用
- 未来分离部署时，仅需将内存 Queue 替换为 Redis `PUBLISH/SUBSCRIBE`，运行时代码不变

**实现方案**:
```python
# 管理端写操作完成后：
await event_bus.publish(ConfigChangeEvent(type="tool.enabled", object_id=tool_id, ...))

# 运行时订阅：
async for event in event_bus.subscribe():
    config_cache.apply(event)
```

**SSE 端点**: `GET /api/v1/events/stream`

**备选方案（已评估，暂不采用）**:
- Redis Pub/Sub：需额外基础设施，V1 阶段增加部署复杂度
- WebSocket：双向通信过重，SSE 单向推送已满足需求
- DB 轮询：违反 FR-016 解耦要求

---

## 5. 运行时配置缓存策略

**决策**: 运行时启动时全量拉取 + SSE 增量更新 + 本地内存缓存

**启动流程**:
1. 调用 `GET /api/v1/config/snapshot` 获取完整配置快照
2. 建立 SSE 连接 `/api/v1/events/stream` 订阅后续变更
3. SSE 断线 → 自动重连，重连后拉取增量（按时间戳）
4. 管理端不可用 → 使用最后成功缓存的配置继续服务（FR-016）

---

## 6. 数据库迁移策略（SQLite → MySQL）

**决策**: SQLAlchemy 2.x async ORM + Alembic 迁移管理，`DATABASE_URL` 控制切换

```bash
DATABASE_URL=sqlite+aiosqlite:///./dev.db        # 开发
DATABASE_URL=mysql+aiomysql://...?charset=utf8mb4 # 生产
```

---

## 7. 前端 UI 设计原则（来自 POC 分析）

**借鉴 POC 的优秀模式**:
- **工作流页面**（Workflow.js）：三栏布局（配置/沙盒/意图映射）+ 内联模型选择弹窗 + 参数滑块
- **MCP 广场**（Agents.js）：卡片网格 + 类型标签筛选 + 搜索框 + 启用/禁用 Toggle
- **模型管理**（ModelSettings.js）：表格列表 + 状态标签 + 新建配置弹窗（API Key 加密显示）

**调整点**:
- 商场条目区分 Tool/Skill/Agent 三类，筛选维度增加"类型"
- 运行时状态（SSE 连接状态）在管理界面可见
- 模型配置支持测试连通性操作

---

所有 NEEDS CLARIFICATION 已解决，技术选型已基于官方文档确认。

**参考资料**:
- [DeepAgents GitHub](https://github.com/langchain-ai/deepagents)
- [DeepAgents 官方文档](https://docs.langchain.com/oss/python/deepagents/overview)
- [LangChain & LangGraph 1.0 发布公告](https://blog.langchain.com/langchain-langgraph-1dot0/)
- [LangGraph 1.0 GA](https://changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available)
