## Jarvis 架构说明（V2）

> 本文档描述当前代码实现（`src/`）对应的真实架构。  
> 重点：Tool 层重构、Agent 全结构化、长期记忆接入。

---

## 1. 架构目标

Jarvis V2 的核心目标：

- Tool 体系从“字典 + 函数”升级为“注册中心 + 执行器 + 统一结果模型”。
- Agent 从单类实现升级为分层类协作（App / Orchestrator / Session / Planner / Memory）。
- 保持 CLI 可持续交互，并支持跨会话记忆。

---

## 2. 顶层分层图

```mermaid
flowchart TD
    cli[CLI_main.py] --> app[AgentApp]
    app --> orchestrator[AgentOrchestrator]
    orchestrator --> session[AgentSession]
    orchestrator --> planner[Planner]
    orchestrator --> memory[MemoryService]
    orchestrator --> llm[LLMGateway]
    orchestrator --> executor[ToolExecutor]
    executor --> registry[ToolRegistry]
    registry --> builtin[BuiltinTools]
```

---

## 3. 关键模块职责

### 3.1 入口与应用装配

- `agent.py`
  - 顶层脚本，转发到 `src.main.main()`。
- `src/main.py`
  - 命令行 REPL：读取用户输入、调用 `AgentApp.chat()`、打印输出。
- `src/agent/app.py`
  - `AgentApp` 负责依赖注入：
    - 创建 `LLMGateway` / `Planner` / `MemoryService` / `AgentOrchestrator`
  - `AgentAppConfig` 统一控制 provider、planner 开关、迭代上限、memory 后端等。

### 3.2 Agent 编排层

- `src/agent/orchestrator.py`
  - `AgentOrchestrator` 是主流程核心：
    1. 记录用户输入（会话）
    2. 调用 LLM
    3. 处理 tool_calls（通过 `ToolExecutor`）
    4. 追加 tool 消息并继续循环
    5. 产出 `AgentResponse`
- `src/agent/session.py`
  - `AgentSession` 管理消息历史：
    - `append_user`
    - `append_assistant`
    - `append_assistant_tool_calls`
    - `append_tool_message`
- `src/agent/planner.py`
  - `Planner` 提供规划提示与步骤占位能力（可开关）。
- `src/agent/response.py`
  - `AgentResponse` 统一输出结构（`content` / `steps` / `metadata`）。

### 3.3 Tool 层（重构后）

- `src/tools/base.py`
  - `ToolSpec`：工具描述模型
  - `BaseTool`：工具抽象基类
  - `FunctionTool`：普通 Python 函数的工具适配器
  - `ToolResult`：统一结果模型
- `src/tools/registry.py`
  - `ToolRegistry`：统一注册、查询、导出 OpenAI tools schema。
  - 同时支持：
    - 装饰器注册：`registry.tool(...)`
    - 显式注册：`registry.register_function(...)`
- `src/tools/executor.py`
  - `ToolExecutor` 负责执行工具调用、解析参数、归一化异常。
- `src/tools/bootstrap.py`
  - 提供全局单例：
    - `tool_registry`
    - `tool_executor`
    - `tool`（装饰器入口）
- `src/tools/builtin/basic.py`
  - 内置示例工具：
    - `get_current_time`（装饰器注册）
    - `add_numbers`（显式注册）

### 3.4 LLM 网关层

- `src/engine/base.py`
  - `LLMGateway`：唯一 LLM 调用入口，屏蔽 provider 差异。

### 3.5 配置层

- `src/config.py`
  - `MODEL_CONFIG` / `DEFAULT_PROVIDER`
  - `AGENT_CONFIG`（`max_iterations`、`enable_planner`、`memory_backend`、`memory_file_path`）

### 3.6 长期记忆层

- `src/agent/memory.py`
  - `BaseMemoryStore`：存储抽象
  - `FileMemoryStore`：文件持久化实现
  - `MemoryService`：
    - 启动时提供记忆上下文（注入 system prompt）
    - 运行时解析用户输入并更新持久化记忆（当前支持名字、语言偏好）

---

## 4. 运行时数据流

```mermaid
sequenceDiagram
    participant U as User
    participant M as MainCLI
    participant A as AgentApp
    participant O as Orchestrator
    participant L as LLMGateway
    participant E as ToolExecutor
    participant R as ToolRegistry
    participant S as MemoryService

    U->>M: 输入文本
    M->>A: chat(user_input)
    A->>O: run(user_input)
    O->>S: observe_user_input()
    O->>L: chat(messages, tools_schema)
    L-->>O: assistant 或 tool_calls
    alt 有 tool_calls
        O->>E: execute_tool_call()
        E->>R: get(tool_name)
        R-->>E: tool impl
        E-->>O: tool result message
        O->>L: chat(updated_messages, tools_schema)
    end
    L-->>O: final content
    O-->>A: AgentResponse
    A-->>M: content
    M-->>U: 输出回答
```
---
## 5. 设计理念与分层优势

### 5.1 `AgentApp`：应用壳与组装器

- **职责**：集中负责依赖注入和应用装配，把 `LLMGateway` / `Planner` / `MemoryService` / `AgentOrchestrator` 等组件组合在一起，对外只暴露简单的 `chat(user_input)` 接口。
- **优势**：
  - 把「应用形态」（命令行、HTTP 服务等）与「Agent 内部逻辑」解耦。
  - 更容易在不同运行方式之间切换，只需更换入口，不必修改 Agent 内核。

### 5.2 Agent 编排层：专注“如何用 LLM + 工具解决问题”

- **职责**：`AgentOrchestrator` + `AgentSession` + `Planner` + `MemoryService` 一起，负责：
  - 如何组织多轮对话。
  - 何时调用工具、如何处理 tool_calls。
  - 何时读取/写入长期记忆。
- **优势**：
  - 高内聚：只关心智能流程本身，不关心底层 API/网络细节。
  - 易演进：将来加多 Agent 协作、更复杂的规划与记忆策略，只需扩展这一层。
  - 易测试：可以通过 fake 的 `LLMGateway` 来单测 Orchestrator 的流程逻辑。

### 5.3 `LLMGateway`：屏蔽 LLM 提供商差异

- **职责**：统一承担与底层 LLM 服务通信的细节：
  - 选用哪个 provider（deepseek / gemini 等）。
  - 使用什么 base_url / api_key / model 名。
  - 调用哪个 SDK、如何传递 `messages` 和 `tools`。
- **优势**：
  - 上层只需调用 `chat(messages, tools)`，像调用普通函数一样使用 LLM。
  - 更换模型提供商或接入本地模型时，只需要更改配置或替换 Gateway 实现。
  - 便于横切能力（重试、超时、日志、成本统计）集中在一处实现，而不污染 Agent 代码。
  - **特别适合 mock 测试**：在测试环境中可以注入一个假的 Gateway，只返回预设的 `message/tool_calls`，无需真正访问网络，就能验证 Agent 的决策与流程。

整体协作可以概括为：

- `AgentApp` 负责“把部件装好，提供一个统一入口”；
- Agent 编排层负责“拿到用户输入后，如何合理地使用 LLM 与工具”；
- `LLMGateway` 负责“具体怎么跟某个 LLM 服务打交道”。
---

## 6. 扩展建议

- 新增工具：在 `src/tools/builtin/` 添加模块并注册，无需改 Orchestrator 主循环。
- 替换记忆后端：实现新的 `BaseMemoryStore`（如 SQLite/Redis）后注入 `MemoryService`。
- 增强 Planner：把占位规划升级为真实“计划-执行-验证”链路。
- 生产化：日志与打点见 `docs/OBSERVABILITY.md`；可在此基础上增加追踪、重试与测试覆盖。

---

## 7. 与学习文档关系

- `docs/TEACHING_PLAN.md`：学习路径与阶段目标。
- 本文档：当前代码真实架构快照。

当你重构组件边界时，应优先更新本文档的：

- 分层图
- 关键模块职责
- 运行时数据流

