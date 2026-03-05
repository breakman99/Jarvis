# Tool 层设计

> 工具层仅保留“继承 `BaseTool` 的类实现”这一种模式；所有工具通过 `registry.register(...)` 显式注册。

---

## 1. 设计目标

- 工具对 LLM 暴露统一 schema，执行返回统一结果。
- 新增工具不改编排主循环，仅新增类并注册。
- 工具代码按业务语义分层，避免单文件堆叠和隐式注册。

---

## 2. 分层结构

```text
src/domain/tools/
  spec/
    base.py                 # ToolSpec / ToolResult / BaseTool
  runtime/
    context.py              # RequestContext / ToolContext
    executor.py             # ToolExecutor / ToolExecution
  registry/
    registry.py             # ToolRegistry（仅 register/get/list/has）
  catalog/
    builtin/
      get_current_time_tool.py
      add_numbers_tool.py
      http_get_tool.py
      http_post_json_tool.py
      common.py             # 内置 HTTP 工具共享逻辑
    defaults.py             # DEFAULT_TOOL_CLASSES + register_default_tools
  bootstrap/
    factory.py              # create_tooling(register_defaults=True)
```

---

## 3. 核心组件

- `ToolSpec`：工具名称、描述、参数 schema、幂等性标记。
- `ToolResult`：工具执行结果，统一 `ok/content/error/metadata`。
- `BaseTool`：工具抽象基类，所有业务工具必须继承。
- `ToolRegistry`：只负责“类实例注册 + 查询 + schema 导出”。
- `ToolExecutor`：参数解析、参数 schema 校验、执行、异常归一化、重试与可观测性打点。
- `register_default_tools`：统一注册内置工具类，避免装配逻辑散落。

补充约束：

- 执行日志中的工具参数会做敏感字段脱敏（如 `authorization`、`token`、`api_key`）。
- 内置 HTTP 工具包含基础 SSRF 防护：仅允许 `http/https`，默认拦截本地/内网地址，并支持 allowlist/denylist。

---

## 4. 新增工具规范

1. 新建一个继承 `BaseTool` 的类文件（建议“一类一文件”）。
2. 在构造函数中声明 `ToolSpec`。
3. 实现 `execute(args, context)`，返回 `ToolResult`。
4. 在装配阶段调用 `registry.register(YourTool())`。

示例：

```python
from src.domain.tools.spec import BaseTool, ToolResult, ToolSpec


class ExampleTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            ToolSpec(
                name="example_tool",
                description="示例工具",
                parameters={"type": "object", "properties": {}},
                idempotent=True,
            )
        )

    def execute(self, args, context=None):
        _ = args, context
        return ToolResult(ok=True, content="ok")
```

---

## 5. 当前约束

- 不再支持 `FunctionTool`、`register_function`、`@registry.tool(...)`。
- 工具注册仅允许显式类实例注册，确保可读性与可维护性。
