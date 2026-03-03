## Jarvis 项目架构说明

> 版本：v0.1（基于当前代码结构）  
> 目的：帮助你快速理解当前 Agent 框架的整体架构、数据流和扩展点。

---

## 1. 总览：Jarvis 是什么？

Jarvis 是一个**本地可运行的最小 Agent 框架**，核心目标是：

- 使用统一的 `AgentEngine` 封装不同 LLM 提供商（deepseek / gemini）。
- 实现一个带 **工具调用（function calling）循环** 的 `SimpleAgent`。
- 通过 `tools` 目录统一管理可调用的 Python 工具函数及其 Schema。

从用户视角看，只需要运行：

- 启动入口：`python agent.py` 或 `python main.py`
- 输入自然语言问题，Agent 会：
  1. 与 LLM 对话；
  2. 自动决定是否调用工具；
  3. 执行本地 Python 函数；
  4. 综合工具结果给出最终回答。

---

## 2. 目录与模块结构

当前与架构相关的主要文件：

- `agent.py`  
  - 简单的启动脚本：`from main import main`，然后在 `__main__` 中调用 `main()`。

- `main.py`  
  - 应用级入口，负责：
    - 创建 `AgentEngine` 实例。
    - 创建 `SimpleAgent` 实例。
    - 准备一个示例 `prompt` 并调用 `agent.run(prompt)`。

- `config.py`  
  - 模型配置中心，定义：
    - `MODEL_CONFIG`：各 provider 的 `base_url` / `api_key` / `model`。
    - `DEFAULT_PROVIDER`：默认使用的模型提供商。

- `engine/`  
  - `engine/base.py`：`AgentEngine` 的实现。
    - 封装 OpenAI 兼容的 `chat.completions.create` 调用。
    - 根据 provider 从 `MODEL_CONFIG` 中选择 base_url / 模型等。
  - `engine/__init__.py`：暴露 `AgentEngine`。

- `agent/`  
  - `agent/simple.py`：核心 Agent 逻辑 `SimpleAgent`。
    - 维护对话 `messages`。
    - 与 `AgentEngine` 交互。
    - 实现工具调用循环与工具结果写回。
  - `agent/__init__.py`：暴露 `SimpleAgent`。

- `tools/`  
  - `tools/builtin.py`：
    - 具体工具函数实现：
      - `get_current_time()`：返回当前时间。
      - `add_numbers(a, b)`：计算两数之和。
    - 工具注册与 Schema：
      - `AVAILABLE_FUNCTIONS`：函数名 → Python 函数的映射。
      - `TOOLS_SCHEMA`：传给 LLM 的工具描述（名称、说明、参数 Schema）。
  - `tools/__init__.py`：暴露 `AVAILABLE_FUNCTIONS`、`TOOLS_SCHEMA`。

- `TEACHING_PLAN.md`  
  - 学习与实践路线文档（教学用，不参与运行时逻辑）。

---

## 3. 核心组件与职责

### 3.1 `AgentEngine`：LLM 调用引擎

位置：`engine/base.py`

**职责**：

- 抽象底层 LLM 提供商的调用差异，对上层提供统一接口：
  - `chat(messages, tools=None)`。
- 根据传入的 `provider` 从 `MODEL_CONFIG` 中读取：
  - `base_url`
  - `api_key`
  - `model`
- 使用 `OpenAI` 客户端进行调用（兼容多家模型的 OpenAI 风格 API）。

**关键点**：

- 如果提供了 `tools`，则会：
  - 把 `tools` 传给 `chat.completions.create`。
  - 设置 `tool_choice="auto"` 让模型自行决定是否调用工具。

---

### 3.2 `SimpleAgent`：带工具调用循环的 Agent

位置：`agent/simple.py`

**职责**：

- 维护会话上下文 `self.messages`（system / user / tool / assistant）。
- 通过 `AgentEngine` 与 LLM 对话。
- 解析 LLM 返回的 `tool_calls`，调用本地工具函数，并将结果写回对话历史。
- 控制循环次数，避免死循环。

**关键属性**：

- `self.engine`：一个 `AgentEngine` 实例。
- `self.messages`：初始化时包含一个 system 提示：
  - `{"role": "system", "content": "你是一个严谨的助手。请善用工具回答问题。"}`。

**关键方法**：

- `handle_tool_calls(tool_calls)`  
  - 遍历每一个 tool_call：
    - 读出 `func_name`、解析 `func_args`（JSON）。
    - 在 `AVAILABLE_FUNCTIONS` 中查找对应 Python 函数。
    - 调用后得到执行结果 `result`。
    - 将工具执行结果以 `role="tool"` 的消息加入 `self.messages`：
      - 包含 `tool_call_id`、`name`、`content`。

- `run(user_input: str) -> str`  
  - 将用户输入加入 `messages`（`role="user"`）。
  - 启动一个最多 `max_iterations=5` 的循环：
    1. 调用 `self.engine.chat(self.messages, tools=TOOLS_SCHEMA)`。
    2. 取出 `resp_msg = response.choices[0].message`。
    3. 如果没有 `resp_msg.tool_calls`：
       - 说明模型直接给出最终回答，返回 `resp_msg.content`，结束。
    4. 如果有 `tool_calls`：
       - 先把 `resp_msg`（包含 tool_calls 的 assistant 消息）加入 `messages`。
       - 调用 `handle_tool_calls(resp_msg.tool_calls)` 执行工具、写入工具结果。
       - 打印「Agent 正在思考下一步…」，进入下一轮循环。
  - 如果循环用尽还没有得到纯文字回答：
    - 返回 `"达到最大任务循环次数, Agent 未能完成任务。"`。

---

### 3.3 `tools`：工具函数与 Tool Schema

位置：`tools/builtin.py`

**职责**：

- 实现具体可被 LLM 调用的 Python 函数。
- 提供统一的注册表与 Schema 给 Agent 使用。

**工具函数示例**：

- `get_current_time()`  
  - 返回当前系统时间字符串，例如 `"2026-03-03 12:34:56"`。

- `add_numbers(a: float, b: float)`  
  - 返回两数之和的字符串形式。

**注册表**：

- `AVAILABLE_FUNCTIONS`：

  - 字典映射：`函数名字符串 -> Python 函数对象`。
  - 例如：`"get_current_time": get_current_time`。
  - 供 `SimpleAgent.handle_tool_calls` 动态查找并调用。

- `TOOLS_SCHEMA`：

  - 列表，每个元素描述一个工具：
    - `name`：工具名称。
    - `description`：工具使用场景说明。
    - `parameters`：JSON Schema 格式的参数描述（类型、字段、是否必填）。
  - 直接传给 `AgentEngine.chat(..., tools=TOOLS_SCHEMA)`，让模型知道有哪些工具可用。

---

### 3.4 `config`：模型提供商配置

位置：`config.py`

**职责**：

- 集中管理不同 LLM 提供商的信息：
  - `MODEL_CONFIG["deepseek"]` / `MODEL_CONFIG["gemini"]` 等。
  - 每项包含：
    - `base_url`
    - `api_key`
    - `model`
- 提供 `DEFAULT_PROVIDER` 作为默认选项。

**与其他模块关系**：

- `AgentEngine.__init__` 会读取：`target = MODEL_CONFIG[provider]`。
- 未来如果添加更多 provider，只需要：
  - 在 `MODEL_CONFIG` 中新增一项；
  - 在创建 `AgentEngine` 时选择对应 provider。

---

## 4. 调用链路（从 main 到工具执行）

下面是当前 Demo 场景下的典型调用流程：

1. **应用启动**
   - 用户运行：
     - `python main.py` 或 `python agent.py`（后者只是转发到 `main.main`）。

2. **初始化组件（在 `main.py` 中）**
   - 创建引擎：
     - `engine = AgentEngine(provider="deepseek")`
   - 创建 Agent：
     - `agent = SimpleAgent(engine)`

3. **发送用户请求**
   - 准备 `prompt`：
     - 例如：「你好，请问现在几点了？顺便帮我算一下 123.45 加 678.9 等于多少。然后向我问好」。
   - 调用：
     - `result = agent.run(prompt)`

4. **Agent 与 LLM 的循环（在 `SimpleAgent.run` 中）**
   - 将用户消息加入 `self.messages`。
   - 调用 `self.engine.chat(self.messages, tools=TOOLS_SCHEMA)`：
     - `AgentEngine` 将 `messages` 和 `TOOLS_SCHEMA` 交给 LLM。
   - LLM 可能返回：
     - 直接回答（无 `tool_calls`）→ 直接返回给用户。
     - 包含 `tool_calls` → 进入工具执行流程。

5. **工具执行与结果写回**
   - `SimpleAgent` 将包含 `tool_calls` 的 assistant 消息加入 `messages`。
   - 调用 `handle_tool_calls(resp_msg.tool_calls)`：
     - 对每个 tool_call：
       - 在 `AVAILABLE_FUNCTIONS` 中找到对应函数。
       - 解析参数并执行本地函数。
       - 将执行结果以 `role="tool"` 消息追加到 `messages`。

6. **继续询问 LLM**
   - 返回循环开头，再次调用 `self.engine.chat(...)`。
   - 此时 LLM 会同时看到：
     - 用户原始提问。
     - 之前的对话。
     - 刚刚的工具执行结果（tool 消息）。
   - LLM 基于这些信息生成新的回答或新的 `tool_calls`。

7. **结束条件**
   - 某一轮 LLM 返回纯文字回答（无 `tool_calls`）：
     - `SimpleAgent.run` 返回这段文字作为最终结果。
   - 超过 `max_iterations` 次仍未结束：
     - 返回错误提示 `"达到最大任务循环次数, Agent 未能完成任务。"`。

---

## 5. 当前架构的扩展点

基于当前设计，扩展主要集中在以下几个地方：

- **新增 / 扩展工具**
  - 在 `tools/builtin.py` 中新增函数，并注册到：
    - `AVAILABLE_FUNCTIONS`
    - `TOOLS_SCHEMA`
  - SimpleAgent 无需修改即可调用新工具。

- **扩展模型提供商**
  - 在 `config.py` 中为新 provider 添加一项配置。
  - 创建 `AgentEngine(provider="新名字")` 即可切换。

- **增强 Agent 行为**
  - 修改 `SimpleAgent` 的 system prompt，让它：
    - 更善于规划步骤。
    - 更偏向使用工具或更少使用工具。
  - 在 `run` 循环中引入更多状态（如记忆、规划、错误重试等）。

- **对外暴露接口**
  - 目前通过 CLI（直接运行 `main.py`）使用。
  - 可以在此基础上包装成：
    - HTTP API（FastAPI / Flask）。
    - Web UI / CLI 工具等。

---

## 6. 与教学文档的关系

- `TEACHING_PLAN.md` 是你的**学习路线图**，从「理解当前架构」到「多 Agent / 插件化」的分阶段规划。
- `ARCHITECTURE.md`（本文档）则是当前版本的**架构快照**，描述：
  - 模块划分。
  - 职责边界。
  - 运行时调用链路。
  - 可扩展点。

建议的使用方式：

- 在学习过程中：
  - 遇到「这个东西是怎么串起来的？」→ 看 `ARCHITECTURE.md`。
  - 想「下一步学什么？」→ 看 `TEACHING_PLAN.md`。
- 当你对架构有重大调整时：
  - 记得同步更新本文件中的相关章节，让它始终反映当前真实架构。

