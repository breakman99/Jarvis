## Agent 层设计说明

> 负责“如何使用 LLM + 工具”来完成用户请求，是整个 Jarvis 的大脑。

---

## 1. 设计目标

- 将 Agent 相关职责拆分为若干单一职责类，避免“神对象”。
- 支持多轮对话、工具调用、规划提示和长期记忆。
- 便于测试与演进：可以单独 mock LLM 层或 Tool 层来测试决策逻辑。

---

## 2. 主要组件一览

- `src/agent/app.py`
  - `AgentAppConfig`：Agent 运行配置（provider、max_iterations、记忆后端等）。
  - `AgentApp`：应用装配与对外入口，提供 `chat(user_input)`。
- `src/agent/orchestrator.py`
  - `AgentOrchestratorConfig`：Orchestrator 层配置。
  - `AgentOrchestrator`：主循环编排核心。
- `src/agent/session.py`
  - `AgentSession`：管理对话消息历史（`messages`）。
- `src/agent/planner.py`
  - `Planner`：简单的规划辅助（可开关）。
- `src/agent/memory.py`
  - `BaseMemoryStore` / `FileMemoryStore` / `MemoryService`：长期记忆管理。
- `src/agent/response.py`
  - `AgentResponse`：统一的 Agent 输出模型。

---

## 3. AgentApp：装配与入口

位置：`src/agent/app.py`

### 3.1 AgentAppConfig

- 字段：
  - `provider`: 使用的模型提供商（默认 `DEFAULT_PROVIDER`）。
  - `max_iterations`: Orchestrator 的最大迭代次数（来自 `AGENT_CONFIG`）。
  - `enable_planner`: 是否启用 Planner 功能。
  - `memory_backend`: 记忆后端类型（当前支持 `"file"`）。
  - `memory_file_path`: 文件型记忆的存储路径（如 `.jarvis/memory.json`）。

### 3.2 AgentApp

职责：

- 基于 `AgentAppConfig` 构造所有依赖：
  - `LLMGateway`（来自 `src/engine`）
  - `Planner`
  - `MemoryService`（基于 `FileMemoryStore`）
  - `AgentOrchestrator`
- 对外只暴露一个方法：
  - `chat(user_input: str) -> str`

作用：

- 将“启动方式”（CLI / Web / API）与“Agent 内部逻辑”解耦。
- 任何入口只需持有一个 `AgentApp` 实例即可与 Agent 交互。

---

## 4. AgentOrchestrator：主循环编排

位置：`src/agent/orchestrator.py`

### 4.1 AgentOrchestratorConfig

- `max_iterations`: 最多迭代轮数（默认为 5）。
- `system_prompt`: 系统提示词（默认为“你是一个严谨的助手...”）。

### 4.2 AgentOrchestrator

构造参数：

- `engine: LLMGateway`：LLM 网关。
- `tool_registry: ToolRegistry`：工具注册中心。
- `tool_executor: ToolExecutor`：工具执行器。
- `config: AgentOrchestratorConfig`。
- `planner: Planner`（可选）。
- `memory_service: MemoryService`（可选）。

核心方法：

- `run(user_input: str, context: Optional[ToolContext] = None) -> AgentResponse`

执行流程（简化）：

1. **记忆观察**：如果有 `memory_service`，先调用 `observe_user_input` 更新长期记忆。
2. **写入用户消息**：`AgentSession.append_user(user_input)`。
3. **生成规划步骤（可选）**：`planner.plan_steps(user_input)`，用于记录在 `AgentResponse.steps`。
4. **进入循环（最多 `max_iterations` 轮）**：
   - 调用 `engine.chat(messages, tools=schema_from_registry)`。
   - 读取 `resp_msg = response.choices[0].message`。
   - 若 **没有 `tool_calls`**：
     - 视为最终答案：记录到 `AgentSession`，返回 `AgentResponse(content=...)`。
   - 若 **有 `tool_calls`**：
     - 将带有 `tool_calls` 的 assistant 消息记录到 `AgentSession`。
     - 对每个 `tool_call`：
       - 通过 `ToolExecutor.execute_tool_call` 执行工具。
       - 将工具执行结果以 `tool` 消息形式写入 `AgentSession`。
5. 若迭代用尽仍未返回最终答案：
   - 返回 `AgentResponse`，`content` 为错误提示，`metadata` 中标记原因。

### 4.3 Think/Plan/Act/Review 流程（轻量阶段化）

Orchestrator 在保持上述循环不变的前提下，通过 **Planner 注入的 system prompt** 引导模型按阶段工作，并在返回的 `AgentResponse.metadata["phase_log"]` 中记录所经历的阶段，便于观测与后续演进。

- **Think（思考）**：理解问题、结合已有记忆与上下文。由 prompt 引导，不单独占一轮。
- **Plan（规划）**：任务较复杂时，先列出解决步骤再执行；简单任务可省略。步骤占位来自 `Planner.plan_steps()`，并写入 `AgentResponse.steps`。
- **Act（执行）**：每轮若模型返回 `tool_calls`，则执行工具并继续下一轮；本轮记为 `act`。
- **Review（复盘）**：当模型不再发起工具调用、直接给出文本答案时，该轮记为 `review`，并作为最终答案返回。

阶段记录规则：

- 首轮无 `tool_calls`：`phase_log = ['think','plan','review']`。
- 首轮有 `tool_calls`：先记 `['think','plan','act']`；后续每轮有 `tool_calls` 则追加 `'act'`，无则追加 `'review'` 并结束。

当前实现为「轻量级阶段化」：不引入显式状态机，仅通过 prompt + metadata 记录阶段；未来可在此基础上改为严格状态机或更细的阶段解析。

---

## 5. AgentSession：会话消息管理

位置：`src/agent/session.py`

### 5.1 数据结构

- `system_prompt: str`：系统提示词。
- `messages: List[Dict[str, Any]]`：标准 OpenAI 风格消息列表。

### 5.2 关键方法

- `__post_init__`：
  - 在 `messages` 为空时，自动插入一条 system 消息。
- `append_user(content: str)`：
  - 追加用户消息。
- `append_assistant(content: Optional[str])`：
  - 追加普通 assistant 消息。
- `append_assistant_tool_calls(model_message: Any)`：
  - 将模型返回的 `tool_calls` 结构转换为标准 messages 形式并记录。
- `append_tool_message(message: Message)`：
  - 追加工具执行后的 `tool` 消息。

作用：

- 将对话上下文以统一结构管理，方便 LLM 和工具调用共享同一份 `messages`。

---

## 6. Planner：规划层（占位实现）

位置：`src/agent/planner.py`

### 6.1 当前实现

- `Planner.enabled: bool`：是否启用。
- `planning_hint()`：
  - 当启用时，为 system prompt 增加一段“先思考再行动”的提示文案。
- `plan_steps(user_input: str) -> List[str]`：
  - 当前返回一个简单的步骤列表，占位用。

### 6.2 未来演进方向

- 改造为真正的“计划-执行-校验”组件：
  - 先由 LLM 生成显式计划（步骤列表）。
  - 再逐步执行每个步骤，并记录执行结果。
  - 在 `AgentResponse.steps` 中返回更详细的轨迹。

---

## 7. MemoryService：长期记忆

位置：`src/agent/memory.py`

> Memory 层的整体设计细节在 `docs/DESIGN_MEMORY.md` 中，这里只说明与 Agent 的交互点。

交互点：

- 在 Orchestrator 初始化时：
  - 通过 `MemoryService.build_system_context()` 构建记忆提示，并拼接进 system prompt。
- 在每次 `run()` 调用开始时：
  - 调用 `MemoryService.observe_user_input(user_input)`，基于规则更新长期记忆。

当前记忆内容示例：

- 用户名字（通过“我叫 X”“以后叫我 X”等句式提取）。
- 用户偏好语言（通过中文/英文提示提取）。

---

## 8. AgentResponse：输出模型

位置：`src/agent/response.py`

- 字段：
  - `content: str`：最终返回给用户的文本。
  - `metadata: Dict[str, Any]`：一些附加信息（如错误原因、统计等）。
  - `steps: List[str]`：规划/执行过程中记录的步骤列表（可用于 debug 或 UI 展示）。

---

## 9. 测试与扩展建议

- **测试建议**：
  - 使用 fake `LLMGateway`，只返回预设的 `message/tool_calls`，来测试 Orchestrator 的循环逻辑。
  - 使用 fake `ToolExecutor` 来模拟工具成功/失败场景。
  - 使用 `FileMemoryStore` 的临时文件来测试记忆写入与读取。
- **扩展建议**：
  - 引入日志（logging），记录每轮迭代、工具调用和记忆变更。
  - 支持多 Agent 协作：在 `AgentApp` 中装配多个 Orchestrator 或子 Agent。
  - 增加更多 Memory 策略（如基于时间衰减、基于重要度的筛选等）。

