# Tool 层设计

> 统一管理可供 LLM 调用的工具：描述（Schema）、注册、执行与结果归一化；与 OpenAI function calling 对接。工具实现以继承 BaseTool 为主，并保留函数式注册（FunctionTool）便于快速扩展。

---

## 1. 设计目标与约束

- 统一、可扩展的工具框架；新增工具不修改 Agent 编排代码。
- 与 LLM function calling（OpenAI 风格）自然对接。
- **实现方式**：推荐继承 BaseTool（Spec 与 execute 同处一类，便于维护）；简单场景可用 FunctionTool / register_function 做函数式注册。
- 执行路径统一：参数解析、异常捕获、结果归一化为 ToolResult/ToolExecution；可选重试与幂等标记。

---

## 2. 目录与分层

```
src/domain/tools/
  base.py       # 抽象与类型：ToolSpec、ToolResult、BaseTool、FunctionTool
  registry.py   # 注册表：ToolRegistry（register / register_function / tool 装饰器）
  executor.py   # 执行器：ToolExecutor、ToolExecution
  context.py    # 请求上下文：RequestContext（ToolContext）
  factory.py    # 装配入口：create_tooling(register_defaults=True)
  defaults.py   # 框架默认工具（BaseTool 子类）+ register_default_tools(registry)
```

| 组件 | 文件 | 职责 |
|------|------|------|
| ToolSpec / ToolResult / BaseTool / FunctionTool | `base.py` | 工具描述、结果模型、抽象基类与函数适配 |
| ToolRegistry | `registry.py` | 注册、查询、导出 to_openai_tools() |
| ToolExecutor / ToolExecution | `executor.py` | 执行单次调用、解析参数、异常归一化、可选重试 |
| RequestContext（ToolContext） | `context.py` | 请求级上下文（request_id、trace_id、deadline 等） |
| factory | `factory.py` | create_tooling() 创建 registry/executor；可选 register_defaults |
| defaults | `defaults.py` | 框架默认工具（时间、加法、HTTP）以 BaseTool 子类实现；register_default_tools(registry) |

---

## 3. BaseTool 与 FunctionTool

- **BaseTool**：抽象基类，持有 ToolSpec，实现 `execute(args, context?) -> ToolResult`。框架默认工具及业务复杂工具应继承此类，将 Spec 与逻辑放在同一类中。
- **FunctionTool**：将普通函数适配为 BaseTool；参数从 args 映射，若函数签名含 context 则注入。若函数返回 `ToolResult` 则直接使用，否则包装为 `ToolResult(ok=True, content=str(result))`。
- 工具“是什么”（Spec）与“如何执行”（execute）解耦，便于测试与替换。

---

## 4. ToolRegistry

- **register(tool)**：注册 BaseTool 实例；重名抛 ValueError。
- **register_function(name, description, parameters, idempotent, func)**：构造 FunctionTool 并注册，用于函数式工具。
- **tool(name?, description, parameters, idempotent)**：装饰器，等价于 register_function。
- **get(name)**、**has(name)**、**list_tools()**：查询。
- **to_openai_tools()**：返回所有已注册工具的 OpenAI schema 列表。

---

## 5. ToolExecutor 与 ToolExecution

- **ToolExecution**：tool_name、arguments、result (ToolResult)、tool_call_id；to_tool_message() 转为 role=tool 消息。
- **execute(tool_name, arguments, context?, tool_call_id?)**：查表、执行、归一化结果；工具不存在或异常均转为 ToolResult(ok=False)。
- **execute_tool_call(tool_call, context?)**：解析 LLM 的 tool_call（name + JSON arguments），再调用 execute。
- 重试：仅对 idempotent 工具做有限次数重试；可重试异常（超时、连接、5xx）由内部逻辑判定。

---

## 6. 默认工具（defaults.py）

框架提供的开箱即用工具，均为 BaseTool 子类：

- **GetCurrentTimeTool**：获取当前本地时间（idempotent）。
- **AddNumbersTool**：两数相加（idempotent）。
- **HttpGetTool**：HTTP GET，响应截断（idempotent）；依赖 requests。
- **HttpPostJsonTool**：HTTP POST JSON（non-idempotent）；依赖 requests。

通过 `create_tooling(register_defaults=True)` 或显式调用 `register_default_tools(registry)` 注册。

---

## 7. 新增工具方式

**方式一：类实现（推荐）**

1. 在业务侧或 `src/domain/tools/` 下新建模块。
2. 定义类继承 BaseTool，在 `__init__` 中传入 ToolSpec，实现 `execute(args, context) -> ToolResult`。
3. 在装配阶段 `registry.register(YourTool())`；若希望纳入“默认工具”，可在 `defaults.py` 中增加类并加入 `register_default_tools`。

**方式二：函数式注册**

1. 实现函数，参数与 ToolSpec.parameters 一致；可选接收 `context`。
2. 使用 `registry.register_function(name=..., description=..., parameters=..., idempotent=..., func=...)` 或 `@registry.tool(...)` 注册。
3. 若函数需返回失败语义，可直接返回 `ToolResult(ok=False, error="...")`，FunctionTool 会原样透传。

无需改编排层或 Orchestrator 主循环。

---

## 8. 错误与重试约定

- **错误**：工具内异常由 Executor 转为 ToolResult(ok=False)；Agent 可见“工具执行失败: …”类内容。
- **重试**：由 Executor 对 idempotent 工具在可重试异常下做有限重试；非幂等工具不自动重试。

---

## 9. 测试与演进

- 单测：ToolRegistry 注册/查询；ToolExecutor 对缺失工具、异常、重试行为；各 BaseTool 子类 execute 逻辑。
- 演进：ToolResult 结构化 payload；工具级超时/权限；耗时与成本打点。
