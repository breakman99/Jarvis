# Tool 层设计

> 统一管理可供 LLM 调用的工具：描述（Schema）、注册、执行与结果归一化；与 OpenAI function calling 对接。

---

## 1. 设计目标与约束

- 统一、可扩展的工具框架；新增工具不修改 Agent 编排代码。
- 与 LLM function calling（OpenAI 风格）自然对接。
- 描述（Spec）与实现（Python 函数/BaseTool）分离；支持装饰器与显式注册。
- 执行路径统一：参数解析、异常捕获、结果归一化为 ToolResult/ToolExecution；可选重试与幂等标记（见实现与配置）。

---

## 2. 组件与文件

| 组件 | 文件 | 职责 |
|------|------|------|
| ToolSpec / ToolResult / BaseTool / FunctionTool | `src/tools/base.py` | 工具描述、结果模型、抽象与函数适配 |
| ToolRegistry | `src/tools/registry.py` | 注册、查询、导出 to_openai_tools() |
| ToolExecutor / ToolExecution | `src/tools/executor.py` | 执行单次调用、解析参数、异常归一化、可选重试 |
| ToolContext | `src/tools/context.py` | 执行时上下文（session_id、user_id、extra） |
| bootstrap | `src/tools/bootstrap.py` | 全局 tool_registry、tool_executor、tool 装饰器 |
| builtin | `src/tools/builtin/` | 内置工具（basic、http 等） |

---

## 3. ToolSpec 与 BaseTool / FunctionTool

- **ToolSpec**：name、description、parameters（OpenAI schema）；to_openai_schema() 返回 type/function 结构。
- **BaseTool**：持有 spec；抽象 execute(args, context?) -> ToolResult。
- **FunctionTool**：spec + 可调用 func；execute 将 args 映射为 kwargs，若 func 签名含 context 则注入；返回值包装为 ToolResult(ok=True, content=str(result))。
- 工具“是什么”与“如何实现”解耦，便于测试与替换。

---

## 4. ToolRegistry

- **register(tool)**：注册 BaseTool；重名抛 ValueError。
- **register_function(name, description, parameters, func)**：构造 FunctionTool 并注册。
- **tool(name?, description, parameters)**：装饰器，等价于 register_function。
- **get(name)**、**has(name)**、**list_tools()**：查询。
- **to_openai_tools()**：返回所有工具的 OpenAI schema 列表，供 LLMGateway 使用。

---

## 5. ToolExecutor 与 ToolExecution

- **ToolExecution**：tool_name、arguments、result (ToolResult)、tool_call_id；to_tool_message() 转为 role=tool 的标准消息。
- **execute(tool_name, arguments, context?, tool_call_id?) -> ToolExecution**：
  - 工具不存在：返回 ok=False、error="工具不存在: name"。
  - 存在：调用 BaseTool.execute，捕获异常为 ToolResult(ok=False, error=...)。
  - 可选：对网络类/可重试错误做有限次数重试；非幂等工具默认不自动重试（可由元数据标记）。
- **execute_tool_call(tool_call, context?) -> ToolExecution**：从 LLM tool_call 解析 name 与 JSON arguments，委托 execute。

---

## 6. ToolContext

- 字段：session_id、user_id、extra。供需要会话/用户信息的工具使用；由 FunctionTool 按签名注入。

---

## 7. 内置工具

- **basic**：get_current_time（装饰器）、add_numbers（显式注册）。
- **http**：http_get、http_post_json；参数 url/headers/timeout 等；响应长度裁剪；异常由 ToolExecutor 归一化。
- 安全与策略：当前可配置超时与长度上限；后续可增加域名白名单或可访问范围配置。

---

## 8. 错误与重试约定

- **错误**：工具内异常不向外抛，由 Executor 转为 ToolResult(ok=False)；Agent 可见“工具执行失败: …”类内容。
- **重试**：可在 Executor 或具体工具内对超时/5xx 等做有限重试；幂等性由工具元数据或配置控制，避免非幂等操作重复执行。

---

## 9. 新增工具步骤

1. 在 `src/tools/builtin/` 新建模块或扩展现有模块。
2. 实现函数，用 @tool(...) 或 register_function 注册。
3. 确保模块在启动时被导入（如 builtin/__init__.py），无需改 Orchestrator。

---

## 10. 测试与演进

- 单测：ToolRegistry 注册/查询；ToolExecutor 对缺失工具、异常、可选重试的行为。
- 演进：ToolResult 支持结构化 payload（如 metadata）；工具级权限或沙箱；耗时/成本打点。
