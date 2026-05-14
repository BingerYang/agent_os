# Knowledge Base — Agent OS

本目录用于沉淀项目开发过程中经过**实测验证**的技术要点、最佳实践与架构决策摘要。
记录内容来源：代码调研、API 签名实测、官方文档核查、踩坑复盘。

---

## 目录

| 文件 | 主题 | 最后更新 |
|------|------|---------|
| [langchain-deepagents.md](./langchain-deepagents.md) | LangChain 1.x + deepagents 包版本、架构层次、废弃 API、内置 Middleware 栈、HITL 审批、流式输出 | 2026-05-14 |
| [architecture-patterns.md](./architecture-patterns.md) | 单/多 Agent 流水线架构、SSE 事件总线、运行时配置热加载 | 2026-05-14 |

---

## 使用规范

- **只记录已验证的内容**：每条结论须注明验证方式（`inspect.signature` / 单元测试 / 官方文档）
- **版本锁定**：所有 API 记录须附包版本，避免版本漂移导致误用
- **标注变更点**：如后续升级包版本，在对应文档顶部追加"版本变更记录"
- **与 specs 的关系**：specs 记录"做什么"，knowledge 记录"怎么用/为什么这样用"
