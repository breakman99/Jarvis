# Agent 层设计

> 当前路径：`AgentApp -> AgentFactory -> AgentCoordinator -> BaseAgent(Template) -> Planner/Executor(Strategy)`。

---

## 1. 设计目标

- 将 Agent 生命周期抽象为模板方法：`plan -> execute -> build_response`。
- 将规划与执行改造为可插拔策略：`PlannerProtocol` 与 `ExecutorProtocol`。
- 将角色配置声明化：`AgentRoleConfig`。
- 将编排职责收敛到 `AgentCoordinator`，并通过 `AgentRouter` 移除硬编码分发。

---

## 2. 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| AgentApp / AgentAppConfig | `src/application/app.py` | 启动装配，创建 Factory、Coordinator、Memory |
| AgentFactory | `src/domain/agent/runtime/factory.py` | 基于 `AgentRoleConfig` 实例化 `ConfigurableAgent` |
| AgentCoordinator | `src/domain/agent/runtime/coordinator.py` | 记忆更新、路由决策、会话管理、请求编排 |
| BaseAgent / ConfigurableAgent | `src/domain/agent/runtime/base_agent.py` | 模板方法驱动单 Agent 生命周期 |
| PlannerProtocol / LLMPlanner / NullPlanner | `src/domain/agent/planning/planner.py` | 可插拔规划策略 |
| ExecutorProtocol / LoopExecutor | `src/domain/agent/execution/loop_executor.py` | 可插拔执行策略 |
| AgentSession | `src/domain/agent/models/session.py` | 管理对话消息 |
| AgentResponse | `src/domain/agent/models/response.py` | 标准化输出 |

---

## 3. 运行流程

1. `AgentApp.chat()` 创建 `RequestContext`。
2. `AgentCoordinator.run()` 更新 Memory，并通过 `AgentRouter` 选择 Agent。
3. `BaseAgent.run()` 追加用户消息并调用 planner 产出步骤。
4. `LoopExecutor.execute()` 驱动 LLM + Tool 循环，返回 `ExecutionResult`。
5. `BaseAgent` 统一构建 `AgentResponse` 返回给上层。

---

## 4. 兼容性策略

- 保留 `AgentOrchestrator` 作为兼容封装，内部委托 `LoopExecutor`。
- 旧入口 `AgentApp.chat(user_input)` 与 CLI 使用方式不变。

---

## 5. 扩展建议

- 新增角色：添加 `AgentRoleConfig` 并通过 `AgentFactory` 注册即可。
- 新增规划/执行策略：实现 Protocol 并注入 `PlannerRegistry`/`ExecutorRegistry`。
- 新增路由规则：实现 `AgentRouter`（按任务类型、标签或上下文路由）。
