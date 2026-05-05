# Contract: POST /api/v1/query（stream=true）SSE 事件协议

**Version**: v1.1（流式扩展）
**Path**: `POST /api/v1/query`

## Request

```json
{
  "query": "用户输入",
  "pipeline_id": "uuid-string",
  "stream": true,
  "session_id": "sess-xxx"  // 可选
}
```

## SSE Response Stream

Content-Type: `text/event-stream`

每条事件格式：
```
data: <json>\n\n
```

### 事件顺序

```
[可选, 0..N] data: {"type":"thinking","content":"..."}
[可选, 0..N] data: {"type":"tool_start","tool":"<name>"}
[可选, 0..N] data: {"type":"tool_end","tool":"<name>"}
[必须, 1..N] data: {"type":"answer","content":"..."}
[必须, 1]    data: {"type":"done","answer":"...","tools_called":[...],"latency_ms":0,"session_id":"..."}

// 或错误终止：
[必须, 1]    data: {"type":"error","code":40301|40302|50000,"message":"..."}
```

### 保证

- `thinking` 事件仅当 LLM 模型支持思考型输出时出现，普通模型不产生
- `answer` 事件在 `tool_end` 之后（工具调用完成后 LLM 才继续生成文本）
- `done` 事件必为最后一条非错误事件
- `error` 事件出现后流关闭，不再有后续事件

## 非流式响应（stream=false，不变）

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "answer": "...",
    "pipeline_type": "SINGLE_AGENT",
    "tools_called": [],
    "session_id": "...",
    "latency_ms": 0
  }
}
```
