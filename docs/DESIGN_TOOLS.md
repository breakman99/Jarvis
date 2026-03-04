## Tool 层设计说明

> 负责管理和执行所有可供 LLM 调用的“工具”（Python 函数），统一注册、描述与执行路径。

---

## 1. 设计目标

- 提供一个统一的、易扩展的工具框架，方便新增和管理业务工具。
- 与 LLM 的 function calling 接口自然对接（OpenAI 风格）。
- 将“工具描述（Schema）”与“具体实现（Python 函数）”清晰分离。
- 在不修改 Agent 代码的前提下，支持动态扩展工具。

---

## 2. 组件一览

- `src/tools/base.py`
  - `ToolSpec`：工具元信息（名称、描述、参数 Schema）。
  - `ToolResult`：统一结果模型。
  - `BaseTool`：工具抽象基类。
  - `FunctionTool`：对普通 Python 函数的适配实现。
- `src/tools/registry.py`
  - `ToolRegistry`：工具注册中心。
- `src/tools/executor.py`
  - `ToolExecutor`：工具执行与错误归一化。
  - `ToolExecution`：执行一次工具调用的封装。
- `src/tools/context.py`
  - `ToolContext`：工具执行时可选的上下文（session_id 等）。
- `src/tools/bootstrap.py`
  - `tool_registry` / `tool_executor`：全局单例。
  - `tool`：装饰器入口（`@tool(...)`）。
- `src/tools/builtin/basic.py`
  - 内置示例工具：`get_current_time`、`add_numbers`。

---

## 3. 工具描述与实现：ToolSpec / BaseTool / FunctionTool

### 3.1 ToolSpec

位置：`src/tools/base.py`

字段：

- `name: str`：工具名称（供 LLM 调用）。
- `description: str`：工具用途说明。
- `parameters: Dict[str, Any]`：参数 Schema（OpenAI function calling 风格）。

关键方法：

- `to_openai_schema()`：
  - 返回类似：
    ```json
    {
      "type": "function",
      "function": {
        "name": "...",
        "description": "...",
        "parameters": { ... }
      }
    }
    ```
  - 用于直接传给 LLM 接口的 `tools` 参数。

### 3.2 BaseTool 与 FunctionTool

- `BaseTool`：
  - 持有 `spec: ToolSpec`。
  - 抽象方法 `execute(args, context) -> ToolResult`。
- `FunctionTool`：
  - 接受 `spec` + 普通 Python 函数 `func`。
  - 在 `execute()` 中：
    - 将 `args` 映射为 `func` 的关键字参数。
    - 如果 `func` 签名包含 `context` 参数，则自动注入 `ToolContext`。
    - 将返回值包装为 `ToolResult`（将结果转为字符串）。

作用：

- 把“工具是什么（Spec）”和“工具怎么写（Python 函数）”解耦。

---

## 4. 工具注册：ToolRegistry

位置：`src/tools/registry.py`

### 4.1 注册与查询

核心方法：

- `register(tool: BaseTool)`：
  - 直接注册一个工具实例（通常由框架内部使用）。
- `register_function(name, description, parameters, func)`：
  - 将普通函数包装为 `FunctionTool` 并注册。
- `tool(name?, description, parameters)`：
  - 返回一个装饰器，用于修饰普通函数：
    ```python
    @tool(
        description="获取当前时间",
        parameters={"type": "object", "properties": {}},
    )
    def get_current_time() -> str:
        ...
    ```
- `get(name: str) -> Optional[BaseTool]`：
  - 根据名称获取已注册工具。
- `has(name: str) -> bool`：
  - 检查某工具是否已存在。
- `list_tools() -> List[BaseTool]`：
  - 返回所有已注册工具。

### 4.2 导出给 LLM：to_openai_tools

- `to_openai_tools() -> List[Dict[str, Any]]`：
  - 遍历所有工具，调用 `tool.spec.to_openai_schema()`。
  - 得到可直接传给 LLM 的 `tools` 列表。

---

## 5. 工具执行：ToolExecutor 与 ToolExecution

位置：`src/tools/executor.py`

### 5.1 ToolExecution

- 字段：
  - `tool_name: str`
  - `arguments: Dict[str, Any]`
  - `result: ToolResult`
  - `tool_call_id: Optional[str]`
- 方法：
  - `to_tool_message()`：
    - 将执行结果转换为标准的 `tool` 消息：
      ```python
      {
          "role": "tool",
          "tool_call_id": ...,
          "name": tool_name,
          "content": result.to_message_content(),
      }
      ```

### 5.2 ToolExecutor

职责：

- 从 `ToolRegistry` 中查找工具。
- 统一执行工具，实现错误捕获与结果包装。

关键方法：

- `execute(tool_name, arguments, context, tool_call_id) -> ToolExecution`：
  - 若工具不存在：
    - 返回 `ok=False`、错误信息为“工具不存在: name”。
  - 若存在：
    - 调用对应 `BaseTool.execute`，将异常捕获为 `ToolResult(ok=False, error=...)`。
- `execute_tool_call(tool_call, context) -> ToolExecution`：
  - 针对 LLM 返回的 `tool_call` 结构：
    - 解析 `tool_call.function.name` 和 JSON 字符串 `arguments`。
    - 将 `tool_call.id` 作为 `tool_call_id` 带入。

作用：

- Agent 不关心工具具体是如何查找或执行的，只需将 `tool_call` 交给 Executor 即可。

---

## 6. ToolContext：执行上下文

位置：`src/tools/context.py`

- 字段：
  - `session_id: Optional[str]`
  - `user_id: Optional[str]`
  - `extra: Dict[str, Any]`
- 作用：
  - 为工具提供附加的上下文信息（如会话 ID、用户 ID 等），便于工具做更复杂的逻辑或日志记录。
  - 通过 `FunctionTool` 的 `context` 参数机制传入具体工具函数。

---

## 7. 全局入口：bootstrap 与 builtin 工具

位置：`src/tools/bootstrap.py`、`src/tools/builtin/basic.py`

### 7.1 bootstrap：统一单例与装饰器

- `tool_registry = ToolRegistry()`：全局注册中心。
- `tool_executor = ToolExecutor(tool_registry)`：全局执行器。
- `tool(...)`：
  - 一个装饰器工厂，本质上调用 `tool_registry.tool(...)`。

### 7.2 builtin.basic：内置工具示例

- `get_current_time()`：
  - 使用 `@tool(...)` 装饰器注册。
  - 无参数，返回当前系统时间字符串。
- `add_numbers(a: float, b: float)`：
  - 普通函数。
  - 通过 `tool_registry.register_function(...)` 显式注册。

示例：

```python
@tool(
    description="获取当前时间。用于回答时间、日期相关问题。",
    parameters={"type": "object", "properties": {}},
)
def get_current_time() -> str:
    ...

def add_numbers(a: float, b: float) -> str:
    return str(a + b)

if not tool_registry.has("add_numbers"):
    tool_registry.register_function(
        name="add_numbers",
        description="加法计算器...",
        parameters={...},
        func=add_numbers,
    )
```

---

## 8. 联网工具（HTTP）

位置：`src/tools/builtin/http.py`。

提供通用 HTTP 能力，供 Agent 在需要时访问外部 API 或网页内容，与现有 Tool 框架（ToolRegistry + ToolExecutor）完全兼容。

### 8.1 工具列表

| 工具名 | 说明 | 主要参数 |
|--------|------|----------|
| `http_get` | 发起 GET 请求，返回响应正文（文本或 JSON 字符串） | `url`（必填）, `headers`, `timeout` |
| `http_post_json` | 发起 POST 请求，请求体为 JSON | `url`（必填）, `json_body`, `headers`, `timeout` |

### 8.2 接口与参数

- **http_get**
  - `url: str`：完整 HTTP/HTTPS 地址（必填）。
  - `headers: Optional[Dict[str, str]]`：可选请求头。
  - `timeout: Optional[float]`：超时秒数，默认 15。
  - 返回：响应正文；若 Content-Type 含 `json` 则解析后以 JSON 字符串形式返回；否则返回原始文本。长度超过约定上限会截断并注明。

- **http_post_json**
  - `url: str`：完整 URL（必填）。
  - `json_body: Optional[Dict[str, Any]]`：POST 的 JSON 体，默认 `{}`。
  - `headers` / `timeout`：同上。

### 8.3 返回与错误约定

- **成功**：工具函数返回字符串，由 `ToolExecutor` 包装为 `ToolResult(ok=True, content=...)`。
- **失败**：网络错误或非 2xx 状态时，`requests` 抛出异常，由 `ToolExecutor` 捕获并包装为 `ToolResult(ok=False, error=异常信息)`，Agent 可见“工具执行失败: …”的 message。

### 8.4 安全与裁剪策略

- **长度裁剪**：单次响应最大保留字符数（如 8000）由模块内常量控制，超出部分截断并在末尾注明，避免输出过长挤占上下文。
- **域名与安全**：当前未做域名白名单；在工具描述中已约束“url 必须是完整的 HTTP/HTTPS 地址”。未来可在本模块或配置中增加允许的域名模式或开关，由配置控制可访问范围。

与 Agent 的集成：无需修改 Orchestrator，只要 `ToolRegistry` 在启动时加载了 `builtin.http`（通过 `builtin/__init__.py` 导入），LLM 即可在合适场景下选择 `http_get` / `http_post_json`。

---

## 9. 如何新增一个工具

新增工具的推荐步骤：

1. 在 `src/tools/builtin/` 下新建一个模块（例如 `file_ops.py`）。
2. 在模块中编写工具函数：
   - 简单场景：用 `@tool(...)` 装饰器注册。
   - 复杂场景：先写普通函数，再用 `tool_registry.register_function(...)` 注册。
3. 在 `src/tools/builtin/__init__.py` 中导出该模块中的工具（非必须，但有利于 IDE 提示）。
4. 无需修改 Orchestrator 或 Engine，Agent 会自动从 `ToolRegistry` 中获取最新工具列表。

---

## 10. 测试与演进建议

- **测试建议**：
  - 单测 `ToolRegistry` 注册/查询逻辑。
  - 单测 `ToolExecutor` 对各种参数和异常的处理。
  - 对重要工具函数编写独立单元测试（不经过 LLM）。
- **演进方向**：
  - 对 ToolResult 支持更丰富的结构（如 JSON payload）。
  - 为工具增加权限控制或安全沙箱。
  - 将工具元数据（如代价、耗时统计）接入监控系统。

