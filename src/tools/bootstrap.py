"""
工具装配入口：create_tooling() 创建 ToolRegistry + ToolExecutor，可选注册内置工具。

应用层（如 AgentApp）在启动时调用 create_tooling(register_builtin=True) 得到 registry/executor
并注入 Coordinator/Orchestrator；兼容通过 tool_registry / tool_executor 的旧式导入。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .executor import ToolExecutor
from .registry import ToolRegistry


def create_tooling(*, register_builtin: bool = True) -> tuple[ToolRegistry, ToolExecutor]:
    """创建工具注册表与执行器；register_builtin=True 时注册 builtin 模块中的工具。"""
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    if register_builtin:
        from .builtin import register_builtin_tools
        register_builtin_tools(registry)
    return registry, executor


# 向后兼容：供装饰器 @tool(...) 等 legacy 用法使用
tool_registry, tool_executor = create_tooling(register_builtin=True)


def tool(
    *,
    name: Optional[str] = None,
    description: str,
    parameters: Dict[str, Any],
    idempotent: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return tool_registry.tool(
        name=name,
        description=description,
        parameters=parameters,
        idempotent=idempotent,
    )

