# Feature Specification: Query 接口真实流式输出

**Feature Branch**: `002-query-llm-streaming`
**Created**: 2026-05-05
**Status**: Draft
**Input**: User description: "针对query接口要支持流和非流接口，现在接口query的流式场景：针对大模型llm的输出结果并非为流式输出的，需要结合下游以及后置检测等规划实现。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 流式对话逐字回显 (Priority: P1)

调用者通过 `POST /api/v1/query`（`stream=true`）与已发布 Agent 对话，期望在大模型生成期间逐步看到文字出现，而不是等待全部结果后一次性展示。

**Why this priority**: 这是流式功能的核心价值。当前用户发起请求后页面无响应直至生成完成，体验差；真实流式输出可让用户即时感知 AI 在"思考"，显著改善交互体验，也是对话演示页面的基础。

**Independent Test**: 发送 `stream=true` 请求后，SSE 连接建立，在大模型生成第一个 token 后 5 秒内前端就应收到第一个 `answer` 类型事件，且内容逐步追加，全部完成后收到 `done` 事件。

**Acceptance Scenarios**:

1. **Given** 已发布的单 Agent 有有效 LLM 配置，**When** 发送 `stream=true` 的 query 请求，**Then** 前端在首 token 到达后立即开始收到字符块（chunk），而非等待全量响应。
2. **Given** 大模型需 10 秒生成完整回复，**When** 发送流式请求，**Then** 前端在第 1-2 秒内开始展示内容，用户无需等待 10 秒白屏。
3. **Given** 流式请求进行中，**When** 大模型生成完成，**Then** 收到 `done` 事件，包含完整 answer、tools_called 和 latency_ms。
4. **Given** 发送 `stream=false` 的同步请求，**Then** 行为与现有实现保持一致，返回完整 JSON 响应。

---

### User Story 2 - 流式输出中的工具调用可见性 (Priority: P2)

调用者在流式模式下能看到 Agent 正在调用哪些工具，从而了解 Agent 的执行过程。

**Why this priority**: 工具调用是 Agent 行为的重要中间步骤，在流式场景中展示工具调用事件可以提升透明度，帮助用户理解延迟原因（等待外部工具返回）。

**Independent Test**: 当 Agent 配置了 MCP/HTTP 工具且查询触发工具调用时，流式 SSE 事件流中应出现 `tool_start` 类型事件，包含工具名称。

**Acceptance Scenarios**:

1. **Given** Agent 配置了工具，**When** 大模型决定调用工具，**Then** SSE 流中在 `answer` 事件之前出现 `tool_start` 事件，包含工具名。
2. **Given** 工具调用完成，**Then** SSE 流中出现 `tool_end` 事件。
3. **Given** Agent 未调用任何工具，**Then** 无 `tool_start`/`tool_end` 事件，直接收到 `answer` 和 `done`。

---

### User Story 3 - 流式场景下的后置安全检测 (Priority: P2)

即使在流式输出模式下，后置检测规则（post-detection）依然对最终完整回答执行检查，不因流式改造而失效。

**Why this priority**: 安全检测是平台的核心保障机制。流式改造不能绕过已配置的后置规则。

**Independent Test**: 配置一条后置检测规则，触发拦截条件，发送 `stream=true` 请求，验证流被中断并推送 `error` 事件，而非将违规内容全部推送给客户端。

**Acceptance Scenarios**:

1. **Given** Pipeline 配置了后置检测规则，**When** 大模型生成的完整回答触发规则，**Then** 流被终止，推送 `error`（code 40302）事件给客户端。
2. **Given** 后置检测通过，**Then** 流正常完成，推送 `done` 事件。
3. **Given** 流式输出已部分推送给客户端，**When** 后置检测失败，**Then** 推送终止事件（客户端已收到的部分内容不可召回，但错误需明确告知）。

---

### User Story 4 - 多 Agent 编排的流式支持 (Priority: P3)

多 Agent 流水线（MULTI_AGENT）在流式模式下，汇总结果也以流式方式逐步推送给调用者。

**Why this priority**: 多 Agent 场景聚合耗时更长，流式输出价值更大，但实现复杂度最高。优先级低于单 Agent。

**Independent Test**: 发布一个编排 Agent（含多个子 Agent），发送 `stream=true` 请求，验证汇总阶段的 LLM 输出以流式推送。

**Acceptance Scenarios**:

1. **Given** MULTI_AGENT 流水线，**When** 发送 `stream=true`，**Then** 最终汇总阶段以流式输出，子 Agent 执行阶段推送 `sub_agent_done` 进度事件。
2. **Given** 某个子 Agent 超时，**Then** 流依然继续，超时信息作为 `sub_agent_timeout` 事件推送。

---

### Edge Cases

- 客户端提前断开 SSE 连接时，服务端应停止 LLM 生成，释放资源（AbortController / 取消 token）。
- 大模型生成过程中抛出异常，推送 `error` 事件并关闭流，不留悬空连接。
- 前置检测（pre-detection）失败，在流建立前立即推送 `error` 事件并关闭，不进入生成阶段。
- `stream=false` 与 `stream=true` 共用同一个查询入口，非流式路径不受改造影响。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统 MUST 在 `stream=true` 时以 SSE 协议推送大模型生成的 token chunks，第一个 chunk 需在模型开始生成后尽快推送（不等待全量完成）。
- **FR-002**: 系统 MUST 在流式 SSE 事件流中区分以下事件类型：`answer`（内容块）、`tool_start`（工具调用开始）、`tool_end`（工具调用结束）、`done`（生成完成，含完整元数据）、`error`（异常或规则拦截）。
- **FR-003**: 系统 MUST 在流式模式下完成生成后，仍对完整回答执行所有已配置的后置检测规则；检测失败时推送 `error` 事件并关闭流。
- **FR-004**: 系统 MUST 在前置检测失败时，不进入生成阶段，直接推送 `error` 事件。
- **FR-005**: 系统 MUST 在 `stream=false` 时保持现有同步响应行为不变。
- **FR-006**: 系统 MUST 支持客户端断开时的资源清理（停止生成、关闭上游连接）。
- **FR-007**: `done` 事件 MUST 包含 `tools_called`（调用的工具列表）、`latency_ms`（总耗时）、`session_id`。
- **FR-008**: 多 Agent 流水线在流式模式下，MUST 在子 Agent 执行阶段推送进度事件，汇总阶段以流式推送最终回答。

### Key Entities

- **SSE 事件（StreamEvent）**: type（字符串枚举）、content（可选，answer chunk 内容）、以及按 type 附加的元数据字段。
- **流式 Agent 执行结果**: 从 CompiledStateGraph 以事件流形式产出，包含 LLM token 事件和工具调用事件。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 发送流式请求后，前端在大模型开始生成的 2 秒内收到第一个 `answer` 事件（首 token 时延 ≤ 2s，排除 MCP 工具调用耗时）。
- **SC-002**: 流式响应的完整内容与同参数的同步响应内容一致（一致性验证）。
- **SC-003**: 后置检测失败场景：客户端收到 `error` 事件，不收到任何 `answer` chunk 通过检测后继续传输。
- **SC-004**: `stream=false` 接口在改造后与改造前的响应结构、内容完全兼容（回归验证）。
- **SC-005**: 客户端断开连接后，服务端 LLM 生成任务在 5 秒内终止，不产生资源泄漏。

## Assumptions

- 当前大模型接入层（LiteLLM / LangChain ChatOpenAI）支持流式输出（`streaming=True`），此前为非流式调用；改造需在模型初始化时启用流式。
- `deepagents.create_deep_agent` 返回 LangGraph `CompiledStateGraph`，支持 `astream_events()` API，可逐事件消费生成过程。
- 后置检测需要完整回答才能执行，因此流式场景下需在服务端积累完整 answer 后运行后置检测，检测通过则流已推送完毕（部分 chunks 已发出），检测失败则推送 error 事件。
- 多 Agent 场景（MULTI_AGENT）中，各子 Agent 并行执行不支持逐 token 流式（子 Agent 结果需全量收集后汇总），仅汇总阶段 LLM 以流式推送，P3 优先级。
- 同步模式（`stream=false`）的代码路径不受改造影响，保持独立。
