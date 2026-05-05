# Implementation Plan: Query LLM 真实流式输出 + 思考内容展示

**Branch**: `001-agent-dispatch-platform` | **Date**: 2026-05-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-query-llm-streaming/spec.md`

## Summary

当前 `POST /api/v1/query`（`stream=true`）实为伪流式：等待 LLM 完整回答后一次性推送 SSE，用户体验与非流式相同。本次改造将 LLM 输出改为 token 级真实流式（通过 `astream_events`），同时在流中暴露工具调用事件和思考内容（thinking tokens），前端 ChatPage 同步展示思考过程（可折叠）。后置检测保持有效：累积完整回答后执行检测，失败则推送 error 事件。非流式路径（`stream=false`）完全不受影响。

## Technical Context

**Language/Version**: Python 3.12（后端）、TypeScript + React 18（前端）
**Primary Dependencies**: FastAPI、LangChain ≥ 1.0.0、deepagents 0.5.3、LangGraph（CompiledStateGraph）、Ant Design 5.x
**Storage**: SQLite（开发），MySQL 8.0+（生产）
**Testing**: pytest（后端），vitest（前端）
**Target Platform**: Linux server（后端）、Web browser（前端）
**Performance Goals**: 首 token 延迟 ≤ 2s（排除工具调用耗时）
**Constraints**: 后置检测不可跳过；非流式接口 100% 兼容；不引入新 Python 包依赖

## Constitution Check

| Gate | Status | Note |
|------|--------|------|
| RESTful 接口规范 | ✅ | SSE 走现有 `/api/v1/query` 端点，不新增路径 |
| 技术栈合规（后端） | ✅ | Python 3.12 / FastAPI / LangChain / deepagents |
| 技术栈合规（前端） | ⚠️ | Constitution 约定 Vue 3，当前已切换为 React+Ant Design（历史决策），本次按现状实施 |
| 中文文档优先 | ✅ | 注释、错误消息均使用中文 |
| 测试驱动开发 | ✅ | 每个函数先写测试 |
| 简单性优先 | ✅ | 新增独立函数，不修改非流式路径 |

**Complexity Tracking**：

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| 新增 `stream_single_agent` 独立函数（而非修改现有） | 保护非流式路径不引入回归 | 在 `run_single_agent` 加参数分支会混合职责 |

## Project Structure

### Documentation (this feature)

```text
specs/002-query-llm-streaming/
├── plan.md           ← 本文件
├── spec.md
├── research.md       ← Phase 0 输出
├── data-model.md     ← Phase 1 输出
├── contracts/
│   └── sse-stream-api.md
└── checklists/
    └── requirements.md
```

### Source Code（涉及文件）

```text
backend/src/
├── agents/
│   └── single_agent.py        ← 新增 stream_single_agent()
├── services/
│   └── query_service.py       ← 新增 execute_stream_query()
└── api/v1/
    └── query.py               ← 更新 _stream_response()

frontend/src/
└── pages/
    └── ChatPage.tsx           ← 新增 thinking 事件处理 + Collapse 展示
```

---

## 实现任务

### T1：`stream_single_agent()` — `backend/src/agents/single_agent.py`

在 `run_single_agent` 下方新增独立的 async generator 函数，**不修改** `run_single_agent`。

```python
async def stream_single_agent(
    agent: Agent,
    query: str,
    tools: list[Tool],
    session_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
```

**实现要点**：
1. 与 `run_single_agent` 相同的工具构建（`await _build_tools_with_real_mcp_schemas(tools)`）和 LLM 初始化，但 ChatOpenAI 增加 `streaming=True`
2. 调用 `deep_agent.astream_events({"messages": [...]}, version="v2")`
3. 事件处理逻辑：
   - `on_chat_model_stream` → 提取 chunk.content（区分 str / list 两种格式），yield `{"type":"answer"|"thinking", "content":"..."}`
   - `on_tool_start` → yield `{"type":"tool_start", "tool": event["name"]}`
   - `on_tool_end` → yield `{"type":"tool_end", "tool": event["name"]}`, 记录 tools_called
4. 流结束后 yield `{"type":"__done__", "answer":..., "thinking":..., "tools_called":..., "session_id":..., "latency_ms":...}`
5. 异常 → yield `{"type":"__error__", "message": str(e)}`

### T2：`execute_stream_query()` — `backend/src/services/query_service.py`

在 `execute_query` 下方新增独立 async generator，**不修改** `execute_query`。

```python
async def execute_stream_query(
    db: AsyncSession,
    pipeline_uid: str,
    query: str,
    session_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
```

**实现要点**：
1. 复用 `_load_pipeline`、`_get_enabled_config`、意图路由逻辑（与 `execute_query` 相同）
2. 前置检测失败 → `yield {"type":"error", "code":40301, "message":...}` → return
3. MULTI_AGENT 类型 → 退化为 `execute_query` + 单次推送（P3 延期）：
   ```python
   result = await execute_query(db, pipeline_uid, query, session_id)
   yield {"type": "answer", "content": result["answer"]}
   yield {"type": "done", **result}
   return
   ```
4. SINGLE_AGENT 类型：
   - 累积 `accumulated_answer` 和 `accumulated_thinking`
   - `async for event in stream_single_agent(...)`: 转发公共事件（answer/thinking/tool_start/tool_end），处理 `__done__`/`__error__`
   - `__done__` 后运行后置检测：失败 → `yield error`，通过 → `yield {"type":"done", ...}`

### T3：`_stream_response()` — `backend/src/api/v1/query.py`

替换 `_stream_response` 的实现，其余代码不改动。

```python
async def _stream_response(body: QueryRequest, db: AsyncSession) -> EventSourceResponse:
    async def event_generator() -> AsyncIterator[dict[str, str]]:
        import json
        try:
            async for event in execute_stream_query(
                db, body.pipeline_id, body.query, body.session_id
            ):
                yield {"data": json.dumps(event, ensure_ascii=False)}
        except Exception as e:
            yield {"data": json.dumps({"type":"error","code":50000,"message":str(e)}, ensure_ascii=False)}

    return EventSourceResponse(event_generator())
```

在文件顶部 import 处补充 `execute_stream_query`。

### T4：ChatPage 思考内容展示 — `frontend/src/pages/ChatPage.tsx`

**4.1 接口扩展**

```typescript
interface MessageItem {
  // ...existing fields...
  thinking?: string
  thinking_streaming?: boolean
}
```

**4.2 SSE 事件处理**

在 `handleSend` 的事件解析循环中增加：
```typescript
} else if (evt.type === 'thinking') {
  const chunk = evt.content ?? ''
  accumulatedThinking += chunk
  setMessages(prev =>
    prev.map(m =>
      m.id === agentMsgId
        ? { ...m, thinking: (m.thinking ?? '') + chunk, thinking_streaming: true }
        : m
    )
  )
```

`done` 事件处理时将 `thinking_streaming` 置为 false：
```typescript
finalizeAgent(agentMsgId, {
  content: evt.answer ?? finalAnswer ?? '（无回复）',
  latency_ms: latencyMs,
  tools_called: toolsCalled,
  thinking_streaming: false,  // 新增
})
```

**4.3 思考内容渲染**（在 agent 消息气泡上方）

使用 Ant Design `Collapse`，引入 `import { Collapse } from 'antd'`：

```tsx
{(msg.thinking || msg.thinking_streaming) && (
  <Collapse
    size="small"
    style={{ marginBottom: 8, maxWidth: '72%', marginLeft: 44 }}
    items={[{
      key: '1',
      label: (
        <span style={{ fontSize: 12, color: '#7c3aed', fontWeight: 500 }}>
          💭 思考过程
          {msg.thinking_streaming && (
            <span style={{ marginLeft: 6, opacity: 0.6 }}>▌</span>
          )}
        </span>
      ),
      children: (
        <div style={{
          fontSize: 12, color: '#6b7280',
          whiteSpace: 'pre-wrap', lineHeight: 1.6,
          maxHeight: 240, overflowY: 'auto',
        }}>
          {msg.thinking ?? ''}
        </div>
      ),
    }]}
  />
)}
```

思考面板默认折叠（`defaultActiveKey` 不设置），用户可手动展开。

---

## 验证方案

### 后端单元测试

文件：`backend/tests/unit/test_stream_single_agent.py`
- Mock `ChatOpenAI.astream_events` 返回 `on_chat_model_stream` 事件序列
- 验证 yield 的事件类型顺序：answer → answer → __done__
- 验证 thinking token 提取（list content）
- 验证 tool_start/tool_end 事件

文件：`backend/tests/unit/test_execute_stream_query.py`
- Mock `stream_single_agent`，验证 pre-detection 失败场景 → error 事件
- 验证 post-detection 失败场景 → error 事件（在 answer 之后）
- 验证正常路径 → answer chunks + done

### 集成测试

文件：`backend/tests/integration/test_query_stream.py`
- 发起真实 SSE HTTP 请求（httpx async client）
- 验证事件流格式和顺序
- 验证非流式接口（`stream=false`）响应不变

### 前端验证

1. 启动 dev server（`npm run dev`）
2. 选择已发布 Agent，发送消息
3. 验证文字逐步出现（非一次性）
4. 若模型支持 thinking，折叠面板出现并可展开
5. 思考过程中光标闪烁，完成后停止
6. 工具调用时界面显示 `🔧 <tool>` 标签
