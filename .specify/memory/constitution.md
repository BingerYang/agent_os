<!--
## Sync Impact Report
- **Version change**: N/A（初始模板）→ 1.0.0
- **修改原则**: 全部从占位符替换为具体内容（首次建立）
- **新增章节**:
  - 核心原则 I–V（RESTful 规范、技术栈合规性、中文文档优先、测试驱动开发、简单性优先）
  - 技术栈规范（后端/前端项目结构、数据库规范）
  - 开发工作流程与质量门禁
- **删除章节**: N/A
- **模板更新状态**:
  - `.specify/templates/plan-template.md`: ✅ 无需修改（Constitution Check 节已为动态占位）
  - `.specify/templates/spec-template.md`: ✅ 无需修改
  - `.specify/templates/tasks-template.md`: ✅ 无需修改
- **延迟待办**: 无
-->

# Agent OS Constitution

## 核心原则（Core Principles）

### I. RESTful 接口规范

所有后端 API 接口 MUST 遵循 RESTful 风格，不可妥协：

- 资源命名使用名词复数形式（如 `/users`、`/agents`、`/tasks`）
- HTTP 方法语义明确：GET（查询）、POST（创建）、PUT（全量更新）、PATCH（部分更新）、DELETE（删除）
- 响应使用标准 HTTP 状态码：2xx 成功、4xx 客户端错误、5xx 服务端错误
- 响应体统一为 JSON 格式，包含 `code`、`message`、`data`、`timestamp` 四个顶层字段，其中：`code` 为 0 表示成功，非 0 表示错误
- 所有接口路径包含版本前缀：`/api/v1/`
- BREAKING CHANGE MUST 升级主版本号，旧版本至少维护一个发布周期

**理由**：统一的接口风格降低前后端协作成本，提升系统可维护性和可预测性，同时便于第三方集成。

### II. 技术栈合规性（NON-NEGOTIABLE）

项目 MUST 严格遵守以下技术选型，未经治理流程批准，不得引入替代方案：

**后端**：
- Python 3.12（包管理使用 uv，不使用 pip/poetry/conda）
- FastAPI（Web 框架，不使用 Flask/Django）
- LangChain ≥ 1.0.0（AI 编排框架）
- deepagents（智能体框架）
- MySQL 8.0+（关系型数据库，不使用 SQLite/PostgreSQL）

**前端**：
- Vue 3（渐进式框架，使用 Composition API）
- Element Plus（UI 组件库）
- Vite（构建工具）

**理由**：固定技术栈确保团队知识聚焦、依赖可控、安全审计边界清晰，避免技术选型碎片化。

### III. 中文文档优先

所有项目文档 MUST 使用简体中文编写：

- 规格说明（spec.md）、计划文档（plan.md）、任务清单（tasks.md）MUST 使用中文
- 代码中的业务逻辑注释 MUST 使用中文；纯技术实现注释可使用英文
- 技术术语（HTTP、REST、API、ORM、LangChain 等）可保留英文原文
- 用户可见的错误消息、界面文本 MUST 使用中文
- API 文档（FastAPI 自动生成）的 `description` 字段 MUST 使用中文

**理由**：项目面向中文用户和开发团队，统一文档语言降低沟通摩擦，提升协作效率。

### IV. 测试驱动开发

所有功能模块 MUST 遵循 TDD 流程，不可跳过：

- 先编写测试，确认测试失败（Red），再实现功能（Green），最后重构（Refactor）
- 后端使用 pytest；前端使用 Vitest
- 后端集成测试 MUST 连接真实 MySQL 数据库，禁止 Mock 数据库层
- 每个用户故事（User Story）MUST 有对应的独立可运行测试
- 测试覆盖率 MUST ≥ 80%（后端），关键业务路径 MUST 达到 100%

**理由**：测试驱动确保功能可验证、重构安全、减少回归风险；真实数据库测试防止 Mock 与生产环境差异导致的隐性 Bug。

### V. 简单性优先（YAGNI）

- 禁止为假设性未来需求添加功能或抽象层
- 三处重复代码方可提取公共函数；单处使用场景禁止提前抽象
- 每个模块 MUST 有单一明确职责（单一职责原则）
- 引入任何复杂度 MUST 在 plan.md 的 Complexity Tracking 表中记录理由
- 禁止添加未被需求明确要求的错误处理、降级逻辑、兼容层

**理由**：过度设计增加维护负担；简单设计使系统长期可控，降低新成员上手成本。

## 技术栈规范

### 后端项目结构

```text
backend/
├── src/
│   ├── api/          # FastAPI 路由层（RESTful 端点，按资源分模块）
│   ├── models/       # 数据模型（SQLAlchemy ORM + Pydantic Schema）
│   ├── services/     # 业务逻辑层（与框架解耦）
│   ├── agents/       # deepagents + LangChain 智能体定义
│   └── core/         # 配置、数据库连接、中间件、异常处理
├── tests/
│   ├── unit/         # 单元测试（Mock 外部依赖）
│   ├── integration/  # 集成测试（真实 MySQL）
│   └── contract/     # 接口契约测试
└── pyproject.toml    # uv 管理的依赖声明
```

### 前端项目结构

```text
frontend/
├── src/
│   ├── components/   # Element Plus 二次封装组件
│   ├── views/        # 页面级视图组件
│   ├── stores/       # Pinia 状态管理
│   ├── api/          # 接口调用层（axios 封装，对齐后端 RESTful 路径）
│   └── router/       # Vue Router 路由配置
└── vite.config.ts    # Vite 构建配置
```

### 数据库规范

- MySQL 8.0+，字符集 utf8mb4，排序规则 utf8mb4_unicode_ci
- 所有业务表 MUST 包含：`id`（主键，BIGINT AUTO_INCREMENT）、`created_at`、`updated_at` 字段
- 数据库结构变更 MUST 通过 Alembic 迁移脚本管理，禁止手动修改生产数据库
- 敏感数据（密码、Token）MUST 加密存储，禁止明文持久化

## 开发工作流程与质量门禁

### 分支策略

- `main` 分支受保护，仅通过 Pull Request 合并
- 功能分支命名规范：`###-feature-name`（三位顺序编号）
- 每个功能分支对应一个完整的用户故事或功能模块

### 质量门禁

所有 PR 合并前 MUST 通过以下全部检查：

1. 后端：`pytest` 全部通过，覆盖率 ≥ 80%
2. 前端：`vitest` 全部通过
3. 类型注解完整（mypy 通过）
4. 格式化与静态检查：**`ruff format`** + **`ruff check`**
5. 代码审查：至少一名核心成员审批
6. 规格文档无 `NEEDS CLARIFICATION` 标记残留
7. 中文文档与代码变更同步提交（不允许"先提代码后补文档"）
8. plan.md 的 Constitution Check 节明确标注合规状态

### 接口变更管理

- 非破坏性变更（新增字段、新增端点）：MINOR 版本号递增
- 破坏性变更（字段删除/重命名、端点废弃）：MAJOR 版本号递增，旧版本维护期至少一个发布周期

## Governance

本 Constitution 是项目所有开发决策的最高准则，其优先级高于任何其他文档、个人习惯或口头约定。

**修订程序**：

1. 提出修订 PR，在 PR 描述中说明变更理由、影响的原则范围及迁移方案
2. 至少两名核心成员审批通过
3. 版本号按以下语义化规则递增：
   - MAJOR：删除或重新定义已有原则（不向后兼容）
   - MINOR：新增原则或章节，或实质性扩展现有指导
   - PATCH：措辞澄清、错别字修正、非语义性调整
4. 所有依赖模板（plan-template.md、spec-template.md、tasks-template.md）MUST 同步检查并更新

**合规审查**：

- 每个 plan.md 的 Constitution Check 节 MUST 明确标注是否合规
- 违反原则 MUST 在 plan.md 的 Complexity Tracking 表中记录具体理由
- 每季度执行一次全项目合规回顾

**运行时指导**：参见 `.specify/memory/` 下的相关文档。

**Version**: 1.0.0 | **Ratified**: 2026-04-16 | **Last Amended**: 2026-04-16
