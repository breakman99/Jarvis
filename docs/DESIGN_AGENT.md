# Agent 层设计

> 统一为单一路径：`AgentApp -> AgentCoordinator -> (PlanningAgent + ConversationAgent/Orchestrator)`，不再保留历史 `Planner` 双轨。

---

## 1. 设计目标与约束

- 规划能力统一到 `PlanningAgent`，避免同一请求在多个位置重复规划。
- 执行能力统一到 `AgentOrchestrator`，只负责 LLM/tool 循环与会话推进。
- 记忆更新统一在请求入口（Coordinator 或单次运行入口）处理，避免重复写入。
- 全链路透传 `RequestContext`，支持 trace、超时和取消控制。

---

## 2. 组件与文件

| 组件 | 文件 | 职责 |
|------|------|------|
| AgentAppConfig / AgentApp | `src/agent/app.py` | 配置与依赖装配；统一创建 Coordinator 路径 |
| AgentCoordinator / ConversationAgent / PlanningAgent | `src/agent/coordinator.py` | 多角色协作：先规划再执行 |
| AgentOrchestrator | `src/agent/orchestrator.py` | 执行主循环：LLM 决策与工具调用 |
| AgentSession | `src/agent/session.py` | 管理 messages（system/user/assistant/tool） |
| MemoryService | `src/agent/memory.py` | 记忆读写与 system 上下文构建 |
| AgentResponse | `src/agent/response.py` | 统一输出：content / steps / metadata |

---

## 3. 运行流程

1. `AgentApp.chat()` 创建 `RequestContext`。
2. `AgentCoordinator.run()` 负责记忆观察与会话构建。
3. `PlanningAgent.plan()`（可开关）产出步骤。
4. `ConversationAgent.run()` 委托 `AgentOrchestrator` 执行工具循环。
5. 返回 `AgentResponse(content, steps, metadata)`。

---

## 4. AgentOrchestrator 约束

- 不再承担规划职责，不依赖 `Planner`。
- 输入：`messages + tools + RequestContext`；输出：最终文本与执行元数据。
- 保持幂等执行语义：每次请求显式会话，不复用旧会话对象。

---

## 5. 扩展与测试建议

- 新增 Agent 角色时，优先通过 `AgentCoordinator` 编排，不直接改 Orchestrator。
- 使用 fake `LLMEngineProtocol` + fake `ToolExecutor` 做执行链路测试。
- 保持规划测试与执行测试分层，避免角色职责耦合。
