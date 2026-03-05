## Jarvis 总览

> 面向生产可用的本地 Agent 框架：分层清晰、可插拔存储与多 Agent 协作。

---

## 1. 项目定位

- **目标**：在本地提供结构清晰、可扩展的 Agent 框架，支持 LLM 对话与工具调用、多轮交互、长期记忆与多 Agent 编排。
- **特点**：
  - 严格分层（Interface / Application / Domain / Infrastructure），职责边界明确。
  - 可插拔记忆后端（文件 / SQLite，接口可扩展）。
  - 多 Agent 抽象（BaseAgent）与编排（AgentCoordinator），便于扩展规划/对话/工具等角色。
  - 配置化错误重试与可观测性打点。

---

## 2. 顶层结构

```bash
.
├── agent.py               # 顶层启动脚本（转发至 src.interface.cli.main）
├── src/
│   ├── interface/         # 接口层：CLI 入口（cli.py）
│   ├── application/       # 应用编排层：AgentApp（app.py）
│   ├── domain/            # 领域层
│   │   ├── agent/         # config / models / planning / execution / memory / runtime
│   │   └── tools/         # spec / runtime / registry / catalog / bootstrap
│   └── infrastructure/   # 基础设施：config、llm、common、observability
└── docs/                  # 架构与设计文档
```

---

## 3. 核心数据流

1. 用户在 CLI 输入（`src/interface/cli.py`）。
2. `AgentApp.chat(user_input)` 基于配置通过 `AgentFactory` 装配默认 Agent，并调用 `AgentCoordinator.run()`。
3. 编排层（`AgentCoordinator`）：
   - 更新长期记忆（`MemoryService.observe_user_input`），并基于记忆构建 system prompt。
   - 通过 `AgentRouter` 选择合适 `BaseAgent` 实例。
   - 将请求交给 `BaseAgent` 模板方法：先执行规划策略（`PlannerProtocol`），再执行工具循环策略（`ExecutorProtocol`）。
4. 执行层（默认 `LoopExecutor`）循环调用 `LLMGateway.chat(messages, tools_schema)`，必要时经 `ToolExecutor` 调用工具并写回 tool 消息，直到生成最终回答。
5. 返回 `AgentResponse`，CLI 输出 `content`。

详细分层与时序见 `docs/ARCHITECTURE.md`。

---

## 4. 文档阅读路径

- **快速上手**：`README.md` → 安装与启动。
- **架构与扩展**：`docs/ARCHITECTURE.md`（分层图、模块职责、数据流、扩展点）。
- **模块实现**：按需阅读 `docs/DESIGN_AGENT.md`、`DESIGN_TOOLS.md`、`DESIGN_MEMORY.md`、`DESIGN_LLMGATEWAY.md`。
- **运维与观测**：`docs/OBSERVABILITY.md`。
