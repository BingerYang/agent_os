# LangChain + deepagents 使用要点

**验证日期**: 2026-05-14
**适用版本**: `langchain==1.2.15`、`deepagents==0.5.3`
**验证方式**: `uv run python -c "import inspect; ..."` 实测 + PyPI 版本核查 + 官方文档核对

---

## 目录

1. [包版本基准](#1-包版本基准)
2. [LangChain 1.0 架构层次与废弃 API](#2-langchain-10-架构层次与废弃-api)
3. [create_deep_agent 完整签名](#3-create_deep_agent-完整签名)
4. [deepagents 内置 Middleware 栈](#4-deepagents-内置-middleware-栈)
5. [create_agent 标准 Agent（对比 create_deep_agent）](#5-create_agent-标准-agent)
6. [HumanInTheLoopMiddleware](#6-humanintheloop-middleware)
7. [工具级审批 vs 响应级审批](#7-工具级审批-vs-响应级审批)
8. [外层包裹模式（项目实际使用）](#8-外层包裹模式)
9. [流式输出与 astream_events](#9-流式输出与-astream_events)
10. [已知陷阱与注意事项](#10-已知陷阱与注意事项)

---

## 1. 包版本基准

| 包 | 项目当前版本 | PyPI 最新版（2026-05-14） | 备注 |
|----|------------|--------------------------|------|
| `langchain` | **1.2.15** | 1.2.15（已是最新）| |
| `deepagents` | **0.5.3** | 0.6.1 | API 向后兼容，可升级 |

**参考链接**：
- deepagents PyPI: https://pypi.org/project/deepagents/
- deepagents 文档: https://docs.langchain.com/oss/python/deepagents/overview
- LangChain Middleware 文档: https://docs.langchain.com/oss/python/langchain/middleware/overview
- HumanInTheLoopMiddleware API: https://reference.langchain.com/python/langchain/agents/middleware/human_in_the_loop/HumanInTheLoopMiddleware
- create_deep_agent API: https://reference.langchain.com/python/deepagents/graph/create_deep_agent
- LangChain 1.0 发布公告: https://blog.langchain.com/langchain-langgraph-1dot0/
- LangGraph 1.0 GA: https://changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available
- HITL Blog: https://blog.langchain.com/agent-middleware/

---

## 2. LangChain 1.0 架构层次与废弃 API

> **CRITICAL：LangGraph 是底层运行时，LangChain 是构建于其上的高级 API** —— 这与 1.0 之前的认知完全相反。

LangChain 1.0 于 2025-10-22 正式 GA，架构层次从上到下：

| 层级 | 组件 | 说明 |
|------|------|------|
| 最高层 | **deepagents** | 复杂 Agent 的一体化 harness（本项目主 Agent 引擎）|
| 高层 | **LangChain 1.0** | `create_agent` API + Middleware 体系 |
| 底层运行时 | **LangGraph 1.0** | 状态图、持久化、流式、人机循环 |

### 废弃的旧 API（禁止在新代码中使用）

| 废弃项 | 替代方案 |
|--------|---------|
| `AgentExecutor` | `create_agent`（LangChain 1.0）或 `create_deep_agent`（deepagents）|
| `create_react_agent`（from `langgraph.prebuilt`）| `create_agent`（from `langchain.agents`）|
| LCEL 管道语法（`prompt \| llm \| parser`）| Middleware + `create_agent` |
| `langgraph.prebuilt` 模块 | `langchain.agents`（功能已迁移）|

### pyproject.toml 依赖版本

```toml
langchain = ">=1.0.0"
langgraph = ">=1.0.0"
deepagents = ">=0.1.0"
```

---

## 3. create_deep_agent 完整签名

**导入路径**：
```python
from deepagents import create_deep_agent
```

**完整参数（`inspect.signature` 实测，deepagents 0.5.3）**：
```python
create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware] = (),      # ← 接受 HumanInTheLoopMiddleware
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

**返回值**：`langchain_core.runnables.CompiledStateGraph`

**最小用法（项目当前）**：
```python
from deepagents import create_deep_agent

compiled_graph = create_deep_agent(
    model=llm,
    tools=lc_tools,
    system_prompt=agent.prompt,
)
# 异步调用
result = await compiled_graph.ainvoke({"messages": [HumanMessage(content=query)]})
# 流式调用
async for event in compiled_graph.astream_events(input_data, version="v2"):
    ...
```

**工具注册格式**（`tools` 参数支持三种，混用时均可）：
```python
tools=[
    my_langchain_tool,               # BaseTool 实例（推荐）
    my_python_function,              # 可调用对象（自动转 StructuredTool）
    {"name": "...", "schema": ...},  # dict 格式（MCP 工具场景）
]
```

---

## 4. deepagents 内置 Middleware 栈

`create_deep_agent` 内部已自动注册以下 Middleware，**无需手动添加**：

| Middleware | 作用 |
|-----------|------|
| `MemoryMiddleware` | 从 `AGENTS.md` 文件加载上下文到系统 prompt |
| `SkillsMiddleware` | 动态加载自定义 Python 脚本作为工具 |
| `FilesystemMiddleware` | 文件操作：ls / read / write / edit / glob / grep |
| `SubAgentMiddleware` | 生成具有独立上下文窗口的子 Agent |
| `SummarizationMiddleware` | Token 超限时自动压缩对话历史 |
| `PatchToolCallsMiddleware` | 修正 LLM 工具调用参数格式错误 |

通过 `create_deep_agent(middleware=[...])` 传入的自定义 Middleware 与内置栈**叠加**，不会替换。

---

## 5. create_agent 标准 Agent

`create_agent` 是 LangChain 1.0 的标准 Agent 创建 API（**非 deepagents**），适合**不需要**
SubAgent / 文件系统 / 任务规划等复杂能力的轻量场景。

```python
from langchain.agents import create_agent

agent = create_agent(
    model=llm,
    tools=tools,
    middleware=[pre_check_middleware, post_check_middleware],
)
```

**与 create_deep_agent 的选型对比**：

| 维度 | `create_agent`（LangChain） | `create_deep_agent`（deepagents）|
|------|----------------------------|----------------------------------|
| 内置能力 | 仅工具调用循环 | 规划 / 子 Agent / 记忆压缩 / 文件系统 |
| Middleware 支持 | ✅ | ✅ |
| 适用场景 | 简单工具调用、路由节点 | 复杂多步骤任务、主 Agent |
| 返回值 | `CompiledStateGraph` | `CompiledStateGraph` |
| 项目使用 | 意图路由节点 | 主业务 Agent 节点 |

**自定义 Middleware 写法**（BaseMiddleware，LangChain 1.0）：
```python
from langchain.agents.middleware import BaseMiddleware

class PreDetectionMiddleware(BaseMiddleware):
    async def on_messages(self, messages, config):
        if await detection_service.check_pre(messages[-1].content):
            raise PreCheckRejected("内容违规")
        return messages

class PostDetectionMiddleware(BaseMiddleware):
    async def on_llm_end(self, output, config):
        if await detection_service.check_post(output.content):
            raise PostCheckRejected("输出违规")
        return output
```

> 本项目前后置检测**没有使用** BaseMiddleware，而是用外层包裹（见第 8 节）。
> 上述写法作为备用参考，适合将来把检测逻辑内嵌进 Agent 时使用。

---

## 6. HumanInTheLoopMiddleware

**导入路径（实测确认，langchain 1.2.15）**：
```python
from langchain.agents.middleware import HumanInTheLoopMiddleware
```

**构造函数签名（`inspect.signature` 实测）**：
```python
HumanInTheLoopMiddleware(
    interrupt_on: dict[str, bool | InterruptOnConfig],
    *,
    description_prefix: str = 'Tool execution requires approval'
) -> None
```

**`interrupt_on` 参数语义**：
- key = 工具名（`str`）
- value = `True`（拦截所有调用）或 `InterruptOnConfig`（细粒度配置）

**功能**：在 Agent 调用工具**之前**暂停执行，等待人工决策（approve / edit / reject）。
需要 `checkpointer` 持久化中断状态，通过 `thread_id` 标识对话线程并在审批后恢复。

**使用示例（高风险工具审批场景）**：
```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_deep_agent(
    model=llm,
    tools=[delete_record_tool, send_email_tool],
    middleware=[
        HumanInTheLoopMiddleware(interrupt_on={
            "delete_record": True,
            "send_email": {"allowed_decisions": ["approve", "reject"]},
        })
    ],
    checkpointer=True,  # 生产环境推荐 AsyncRedisSaver 或 AsyncSqliteSaver
)
```

> ⚠️ **checkpointer=True** 在开发环境使用内存 checkpointer，生产需替换为持久化实现（见第 10 节）。

---

## 7. 工具级审批 vs 响应级审批

这是使用 `HumanInTheLoopMiddleware` 前最关键的区分：

| 维度 | 工具级审批 | 响应级审批 |
|------|-----------|-----------|
| **触发时机** | `AIMessage` 生成工具调用后，工具执行前 | Agent 产生最终 answer 后，返回调用方前 |
| **推荐实现** | `HumanInTheLoopMiddleware` + `checkpointer` | 外部异步队列（`DetectionEvent` 表 + `asyncio.Event`）|
| **典型场景** | 危险操作防护（删除记录、发送邮件）| A-03 人机审批策略 |
| **LangGraph 支持** | 原生支持（interrupt_before）| 需在 LangGraph 外部实现 |
| **checkpointer 依赖** | 必须 | 不需要（外部队列持久化）|

**项目决策（A-03 人机审批）**：使用外部异步队列（`detection_approval.py`），不使用
`HumanInTheLoopMiddleware`，原因：
1. A-03 是**响应级**审批（最终答案），语义与**工具级**审批不匹配
2. 使用 HITL Middleware 需要为每个 Agent 配置 `checkpointer`，改动面广
3. 外部队列方案与现有 `query_service.py` 架构更契合，无需侵入 LangGraph 图结构

---

## 8. 外层包裹模式

**项目实际使用的检测执行架构**（来源：`query_service.py`）：

```
query_service.py:
  run_pre_detection(pre_rules, query)      ← LangGraph 外，前置拦截
        ↓ (通过: query 可能已被改写)
  node.execute(agent_ctx)                  ← 内部: CompiledStateGraph.ainvoke()
        ↓ (获得 answer)
  run_post_detection(post_rules, answer)   ← LangGraph 外，后置处置
        ↓
  return answer (可能已被改写/挂起)
```

**为什么选外层包裹而不是 LangChain Callbacks / Middleware**：

| 方案 | 评估 |
|------|------|
| LangChain Callbacks | ❌ 仅观测，无法阻断执行流 |
| `BaseMiddleware`（内嵌 Agent）| ❌ 仍在 LangGraph 内部，P-01 限流需在 LLM 调用前即拦截 |
| `HumanInTheLoopMiddleware` | ❌ 工具调用级中断，不适合请求入口拦截 |
| LCEL 组合 | ❌ 破坏 `astream_events(version="v2")` 流式事件结构 |
| **外层包裹（现有方案）** | ✅ 完整控制执行流，在 LLM 调用前/后均可拦截，符合 YAGNI |

---

## 9. 流式输出与 astream_events

**项目使用方式**（`version="v2"` 是 LangGraph 要求）：
```python
async for event in compiled_graph.astream_events(input_data, version="v2"):
    kind = event["event"]
    if kind == "on_chat_model_stream":
        chunk = event["data"]["chunk"]
        # 处理 token 流
    elif kind == "on_chain_end":
        # 获取最终结果
        ...
```

**注意**：`astream_events` 在外层有 `run_post_detection` 时，需要先收集完整 answer 再执行
后置检测，**不能在 token 流中途中断并改写**。改写型后置策略（`rewrite` action）需要等
流式完成后对完整响应处理。

---

## 10. 已知陷阱与注意事项

### 10.1 `checkpointer=True` 不可用于生产

`create_deep_agent(checkpointer=True)` 使用内存 checkpointer，进程重启后中断状态丢失。
生产环境 HITL 场景需使用：
```python
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

checkpointer = AsyncRedisSaver.from_conn_string("redis://localhost:6379")
```

### 10.2 `interrupt_on` 快捷参数 vs `middleware` 参数

`create_deep_agent` 提供两种配置 HITL 的方式：
- `interrupt_on={"tool_name": True}` — 快捷方式，等价于自动创建 `HumanInTheLoopMiddleware`
- `middleware=[HumanInTheLoopMiddleware(...)]` — 显式方式，支持更细粒度配置

两者不要同时使用（会重复注册）。

### 10.3 deepagents 0.6.1 升级注意

0.6.1 与 0.5.3 API 向后兼容，但升级前应确认：
- `create_deep_agent` 签名无破坏性变更
- `AgentMiddleware` 基类接口未改变
- 运行 `uv run pytest tests/ -k "agent"` 全部通过后再升级

### 10.4 内置 Middleware 与自定义 Middleware 执行顺序

deepagents 内置 Middleware 栈的执行顺序固定，自定义 `middleware=[...]` 插入位置由
deepagents 内部决定（通常在内置栈之后）。如需在内置 Middleware 之前执行，目前只能通过外层包裹实现。
