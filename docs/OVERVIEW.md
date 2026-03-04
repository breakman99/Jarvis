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
├── agent.py               # 顶层启动脚本（转发至 src.main.main）
├── src/
│   ├── main.py            # CLI REPL 入口
│   ├── config.py          # 模型、Agent、记忆、工具与 LLM 配置
│   ├── common/            # 公共错误类型（TransientError / TimeoutError / CancelledError 等）
│   ├── engine/            # LLMGateway 与 LLMReply / LLMEngineProtocol 类型
│   ├── observability/     # 可观测性：metrics（计数/直方图）、audit（审计事件）
│   ├── agent/             # App / Coordinator / Orchestrator / Session / Memory / BaseAgent / Response
│   └── tools/             # Tool 框架与内置工具（registry / executor / context / bootstrap / builtin）
└── docs/                  # 架构与设计文档
```

---

## 3. 核心数据流

1. 用户在 CLI 输入（`src/main.py`）。
2. `AgentApp.chat(user_input)` 装配并调用编排层。
3. 编排层（统一为 `AgentCoordinator`）：
   - 更新长期记忆（MemoryService.observe_user_input）。
   - 将用户输入加入会话（AgentSession）。
   - 调用 LLMGateway.chat(messages, tools_schema) 获取模型决策。
   - 若有 tool_calls，经 ToolExecutor 执行并写回 tool 消息，继续循环。
4. 返回 `AgentResponse`，CLI 输出 `content`。

详细分层与时序见 `docs/ARCHITECTURE.md`。

---

## 4. 文档阅读路径

- **快速上手**：`README.md` → 安装与启动。
- **架构与扩展**：`docs/ARCHITECTURE.md`（分层图、模块职责、数据流、扩展点）。
- **模块实现**：按需阅读 `docs/DESIGN_AGENT.md`、`DESIGN_TOOLS.md`、`DESIGN_MEMORY.md`、`DESIGN_LLMGATEWAY.md`。
- **运维与观测**：`docs/OBSERVABILITY.md`。
