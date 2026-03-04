# Agent 层设计

> 负责“如何使用 LLM + 工具 + 记忆”完成用户请求；定义应用装配、编排循环、会话与响应模型。

---

## 1. 设计目标与约束

- 将 Agent 职责拆分为装配（App）、编排（Orchestrator/Coordinator）、会话（Session）、规划（Planner）、记忆（MemoryService）、响应（AgentResponse），避免神对象。
- 支持多轮对话、工具调用、可开关规划与长期记忆注入。
- 便于测试：可 mock LLMGateway / ToolExecutor / MemoryService 验证编排逻辑。
- 演进路径：当前单 Orchestrator；后续引入 BaseAgent 与 AgentCoordinator 支持多 Agent 协作。

---

## 2. 组件与文件

| 组件 | 文件 | 职责 |
|------|------|------|
| AgentAppConfig / AgentApp | `src/agent/app.py` | 配置与依赖装配，对外 `chat(user_input) -> str` |
| AgentOrchestratorConfig / AgentOrchestrator | `src/agent/orchestrator.py` | 主循环：记忆观察 → 会话更新 → LLM → 工具执行 → AgentResponse |
| AgentSession | `src/agent/session.py` | 管理 messages（system/user/assistant/tool） |
| Planner | `src/agent/planner.py` | 规划提示与步骤占位（可开关） |
| MemoryService | `src/agent/memory.py` | 记忆读写与 system 上下文构建（见 DESIGN_MEMORY） |
| AgentResponse | `src/agent/response.py` | 统一输出：content / steps / metadata |

---

## 3. AgentApp

- **AgentAppConfig**：provider、max_iterations、enable_planner、memory_backend、memory_file_path（及后续 memory_db_path 等）。
- **AgentApp**：根据 config 构造 LLMGateway、Planner、MemoryService、AgentOrchestrator；对外仅暴露 `chat(user_input: str) -> str`。将运行形态（CLI/HTTP）与内核解耦。

---

## 4. AgentOrchestrator

- **依赖**：engine (LLMGateway)、tool_registry、tool_executor、config、planner（可选）、memory_service（可选）。
- **run(user_input, context?) -> AgentResponse**：
  1. 若有 memory_service：`observe_user_input(user_input)`。
  2. `session.append_user(user_input)`；可选 `planner.plan_steps(user_input)` 记入 response.steps。
  3. 循环（≤ max_iterations）：调用 `engine.chat(session.messages, tools)`；无 tool_calls 则视为最终答案并返回；有则 append assistant tool_calls、执行每个 tool_call、append tool 消息后继续。
  4. 用尽迭代则返回带 reason 的 AgentResponse。
- **phase_log**：在 metadata 中记录 think/plan/act/review，便于观测与后续状态机演进。

---

## 5. AgentSession

- **字段**：system_prompt、messages（OpenAI 风格列表）。
- **方法**：append_user、append_assistant、append_assistant_tool_calls、append_tool_message。__post_init__ 在 messages 为空时插入 system 消息。
- 保证 LLM 与工具共享同一份 messages，便于多轮与 tool 结果回放。

---

## 6. Planner

- **当前**：enabled 开关；planning_hint() 返回注入 system 的规划文案；plan_steps(user_input) 返回占位步骤列表。
- **演进**：可升级为 PlanningAgent，产出结构化步骤并交由 Coordinator 分配给执行 Agent。

---

## 7. MemoryService 与 Agent 的协作

- **初始化**：Orchestrator 构造时用 `memory_service.build_system_context()` 拼入 system prompt。
- **每轮开始**：`run()` 开头调用 `memory_service.observe_user_input(user_input)` 更新持久化记忆。
- 详见 `docs/DESIGN_MEMORY.md`。

---

## 8. AgentResponse

- **字段**：content（最终文本）、metadata（phase_log、reason 等）、steps（规划/执行步骤列表）。
- 供 CLI 或上层只取 content，或利用 steps/metadata 做调试与展示。

---

## 9. 错误处理与可观测性

- 编排层不吞异常：LLM 或工具异常向上抛出；由 CLI 或 App 层做统一捕获与用户提示（见实现）。
- 日志：chat 完成、iteration、decision（final_answer / use_tools）、phase_log 等见 OBSERVABILITY.md。

---

## 10. 扩展与测试建议

- **多 Agent**：引入 BaseAgent（plan/build_messages/select_tools/handle_model_output）、ConversationAgent、PlanningAgent；AgentCoordinator 持有 AgentRegistry 并驱动多 Agent 协作。
- **测试**：fake LLMGateway 返回预设 message/tool_calls；fake ToolExecutor 模拟成功/失败；临时 FileMemoryStore 或 SQLite 测记忆读写。
