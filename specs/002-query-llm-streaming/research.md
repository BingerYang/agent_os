# Research: Query LLM 流式输出

**Date**: 2026-05-05
**Phase**: Phase 0 - Research

---

## R-001: `astream_events` 可用性

**Decision**: 使用 `CompiledStateGraph.astream_events(version='v2')`
**Rationale**: `deepagents.create_deep_agent` 返回 LangGraph `CompiledStateGraph`，该类完整支持 `astream_events`。v2 版本比 v1 增加了 `parent_ids` 和 custom events 支持，推荐使用。
**Alternatives considered**: `astream_log` 可用但已不推荐；直接用 `llm.astream()` 绕过 agent 层会丢失工具调用事件。

**关键事件类型**（v2）：
- `on_chat_model_stream` → `event["data"]["chunk"]` 为 `AIMessageChunk`
- `on_tool_start` → `event["name"]` 为工具名
- `on_tool_end` → `event["name"]` 为工具名
- `on_chat_model_end` → `event["data"]["output"]` 为完整 AIMessage

---

## R-002: 思考内容（Thinking Tokens）提取

**Decision**: 统一检测 `AIMessageChunk.content` 是否为 list 类型，提取 `type=="thinking"` 的块

**Rationale**: LangChain 对 Anthropic 思考型模型的流式输出，`content` 字段是 list，每个元素是 `{"type": "thinking"/"text", "thinking"/"text": "..."}` 结构。非思考模型的 `content` 为普通 str，向后兼容。

**思考 token 提取逻辑**：
```python
chunk = event["data"]["chunk"]
if isinstance(chunk.content, list):
    for item in chunk.content:
        if isinstance(item, dict):
            if item.get("type") == "thinking":
                yield {"type": "thinking", "content": item.get("thinking", "")}
            elif item.get("type") == "text" and item.get("text"):
                yield {"type": "answer", "content": item["text"]}
elif isinstance(chunk.content, str) and chunk.content:
    yield {"type": "answer", "content": chunk.content}
```

**当前限制**: 数据库中当前只配置了 `gpt-5.4`（OpenAI 模型），不支持原生 thinking tokens。但架构应对 Anthropic 思考型模型保持兼容，当模型不输出 thinking 时前端不展示思考面板即可。

**Alternatives considered**: 检查 `response_metadata["model_provider"]` 来判断是否为 Anthropic 模型，再分支处理 — 但直接检测 content 类型更健壮，无需维护模型白名单。

---

## R-003: 流式后置检测策略

**Decision**: "先流式推送 tokens，再做后置检测"（Stream-then-detect）

**Rationale**: 后置检测需要完整回答，若先缓冲再流式则对用户无流式价值。Stream-then-detect 在完整回答生成完毕后运行检测，若触发拦截则推送 `error` 事件通知客户端（客户端已收到的部分 chunks 不可召回，这在 spec 中已明确接受）。

**Alternatives considered**:
- 缓冲全量再流式（Buffer-then-stream）：检测可以拦截全部内容，但用户感知与非流式相同，失去意义。
- 流式运行时检测（Rolling check）：复杂度高，现有检测规则均基于完整文本。

---

## R-004: 前端 ChatPage 思考内容展示方案

**Decision**: 使用 Ant Design `Collapse` 组件，默认折叠，用紫色 `💭 思考过程` 标签标识

**Rationale**: 
- `antd` 已作为核心依赖安装，`Collapse` 组件开箱即用，无需新增依赖
- 思考内容通常较长，默认折叠避免干扰主对话流
- 紫色标识（`tag-purple`）与 answer（蓝色）、tools（橙色）视觉区分明确

**MessageItem 新增字段**：
```typescript
thinking?: string           // 累积的思考内容
thinking_streaming?: boolean // 思考是否仍在流式中
```

**SSE 新增事件**：
```json
{ "type": "thinking", "content": "<chunk>" }
```

**Alternatives considered**: 独立的思考气泡（单独消息条目）— 复杂，对话流混乱；内联展开/收起文字区域 — 不如 Collapse 交互清晰。

---

## R-005: `stream_single_agent` 与 `run_single_agent` 共存策略

**Decision**: 新增独立的 `stream_single_agent()` async generator 函数，保持 `run_single_agent()` 不变

**Rationale**: 非流式路径（`stream=false`）调用量大，不应引入任何回归风险。新函数单独负责流式逻辑，职责清晰，符合 Constitution V（简单性优先）。

**Alternatives considered**: 在 `run_single_agent` 内部增加 `streaming` 参数分支 — 增加单一函数复杂度，违反单一职责。

---

## R-006: 多 Agent 流式（MULTI_AGENT）

**Decision**: P3 延期，当前版本不实现 `stream_multi_agent`

**Rationale**: MULTI_AGENT 流水线需要并行子 Agent + 汇总 LLM，架构更复杂。当前 P1/P2 已覆盖主要使用场景（单 Agent 对话演示）。`_stream_response` 对 MULTI_AGENT 退化为"批量推送 done 事件"（当前行为），明确告知用户即可。

---

## R-007: LLM 初始化必须开启 streaming

**Decision**: `stream_single_agent` 内创建 `ChatOpenAI` 时增加 `streaming=True`

**Rationale**: `astream_events` 在没有 `streaming=True` 时仍可工作（会批量返回完整 chunk），但无法做到 token 级别流式。`streaming=True` 确保 ChatOpenAI 发送流式 HTTP 请求，逐 token 产出。

**Implementation note**: `run_single_agent`（非流式路径）保留现有初始化方式，不加 `streaming=True`，避免意外影响。
