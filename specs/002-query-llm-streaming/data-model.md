# Data Model: Query LLM 流式输出

**Date**: 2026-05-05

---

## SSE 流式事件（StreamEvent）

流式响应通过 SSE 协议推送，每条事件为 `data: <json>` 格式。

### 事件类型定义

```typescript
// 思考内容块（LLM 内部推理，仅思考型模型输出）
{ type: "thinking"; content: string }

// 回答内容块（逐 token 推送）
{ type: "answer"; content: string }

// 工具调用开始
{ type: "tool_start"; tool: string }

// 工具调用结束
{ type: "tool_end"; tool: string }

// 生成完成（最终事件）
{
  type: "done"
  answer: string        // 完整回答
  tools_called: string[] // 调用的工具名列表
  latency_ms: number    // 总耗时（毫秒）
  session_id: string
}

// 错误（前置检测失败 / 后置检测失败 / 执行异常）
{
  type: "error"
  code: 40301 | 40302 | 50000
  message: string
}
```

---

## 前端 MessageItem（扩展）

```typescript
interface MessageItem {
  id: string
  role: 'user' | 'agent' | 'error'
  content: string
  latency_ms?: number
  tools_called?: string[]
  streaming?: boolean        // answer 是否仍在流式中
  thinking?: string          // 累积的思考内容（新增）
  thinking_streaming?: boolean // thinking 是否仍在流式中（新增）
}
```

---

## 内部流式事件（backend async generator）

`stream_single_agent` 和 `execute_stream_query` 之间传递的内部事件（Python dict）：

```python
# 对外推送的公共事件（与 SSE 格式一致）
{"type": "thinking",    "content": str}
{"type": "answer",      "content": str}
{"type": "tool_start",  "tool": str}
{"type": "tool_end",    "tool": str}

# 内部结束标记（不推送给客户端，由 execute_stream_query 转化为 "done"）
{
  "type": "__done__",
  "answer": str,
  "thinking": str,
  "tools_called": list[str],
  "session_id": str,
  "latency_ms": int,
}
```

---

## 状态流转

```
client connect
     │
     ▼
pre-detection
  ├─ fail → yield {type:error, code:40301} → close
  └─ pass
       │
       ▼
  stream_single_agent()
     │
     ├─ on_chat_model_stream → yield {type:thinking|answer, content:...}
     ├─ on_tool_start        → yield {type:tool_start, tool:...}
     ├─ on_tool_end          → yield {type:tool_end, tool:...}
     └─ on_chat_model_end    → __done__ (internal)
       │
       ▼
  post-detection (on full accumulated answer)
  ├─ fail → yield {type:error, code:40302} → close
  └─ pass → yield {type:done, ...} → close
```
