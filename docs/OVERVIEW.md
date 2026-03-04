## Jarvis 项目总览

> 面向学习与演进的本地 Agent 框架

---

## 1. 项目定位

- **目标**：在本地构建一个结构清晰、可扩展的 Agent 框架，用来系统学习：
  - LLM 对话与工具调用（function calling）
  - 多轮交互与记忆管理
  - 模块化架构与工程化实践
- **特点**：
  - 代码量刻意保持精简，便于阅读和重构。
  - 所有核心能力（Agent、Tool、Memory、LLM 网关）都有清晰的分层。
  - 文档与代码同步演进，用于教学与自我复盘。

---

## 2. 顶层结构一览

项目根目录下关键内容（简化版）：

```bash
.
├── agent.py               # 顶层启动脚本：python agent.py
├── src/
│   ├── main.py            # CLI 入口：命令行 REPL
│   ├── config.py          # 模型配置 + Agent 运行配置
│   ├── engine/            # LLM 网关（LLMGateway）
│   ├── agent/             # Agent 相关：App / Orchestrator / Session / Planner / Memory
│   └── tools/             # Tool 框架与内置工具
└── docs/
    ├── OVERVIEW.md        # 项目总览（本文）
    ├── ARCHITECTURE.md    # 架构说明（分层视图 + 时序图）
    ├── DESIGN_AGENT.md    # Agent 层详细设计
    ├── DESIGN_TOOLS.md    # Tool 层详细设计
    ├── DESIGN_MEMORY.md   # Memory 层详细设计
    ├── DESIGN_LLMGATEWAY.md # LLMGateway 层详细设计
    └── TEACHING_PLAN.md   # 学习与实践路线
```

---

## 3. 核心数据流（从用户到工具）

高层时序（简化版）：

1. 用户在命令行输入问题（`src/main.py`）。
2. `AgentApp.chat(user_input)` 被调用，负责：
   - 准备 `LLMGateway` / `Planner` / `MemoryService` / `AgentOrchestrator`。
3. `AgentOrchestrator.run(user_input)`：
   - 更新记忆（如用户名字、语言偏好）。
   - 将用户输入加入 `AgentSession.messages`。
   - 调用 `LLMGateway.chat(messages, tools_schema)` 获取模型决策。
   - 若有 `tool_calls`，通过 `ToolExecutor` 调用对应工具。
   - 将工具结果作为 `tool` 消息写回 `messages`，继续下一轮。
4. 最终返回一个 `AgentResponse`，由 `AgentApp` 提取 `content` 返回给 CLI 输出。

详细的序列图与模块职责说明见 `docs/ARCHITECTURE.md`。

---

## 4. 学习建议：如何阅读与使用这些文档

- **第一步：整体把握**
  - 先看 `README.md`（快速了解项目与启动方式）。
  - 再看本文件 `docs/OVERVIEW.md`，对整体结构有一个全局感知。
- **第二步：理解架构**
  - 阅读 `docs/ARCHITECTURE.md`：
    - 看顶层分层图（有哪些层、谁依赖谁）。
    - 看运行时时序图（从 main 到工具执行的全过程）。
- **第三步：按模块深入**
  - 想研究 Agent 行为 → 看 `DESIGN_AGENT.md` + 对应 `src/agent/` 代码。
  - 想扩展工具 → 看 `DESIGN_TOOLS.md` + 对应 `src/tools/` 代码。
  - 想实现更复杂的记忆 → 看 `DESIGN_MEMORY.md`。
  - 想切换模型或加重试逻辑 → 看 `DESIGN_LLMGATEWAY.md`。
- **第四步：照着学习路线实践**
  - `docs/TEACHING_PLAN.md` 提供了分阶段练习建议，可以边读边做小实验。

---

## 5. 面向不同读者的阅读路径

- **如果你是当前项目的作者/学习者**：
  - 建议反复在「代码 ⇄ 架构文档 ⇄ 学习计划」之间来回切换。
  - 每完成一个阶段的改动，都在文档中补充自己的理解与复盘。
- **如果未来有其他人阅读这个项目**：
  - 推荐起点：`README.md` → `docs/OVERVIEW.md` → `docs/ARCHITECTURE.md`。
  - 然后根据兴趣选择具体设计文档继续深入。

