"""
工具层装配入口：create_tooling() 创建 ToolRegistry + ToolExecutor，可选注册默认工具。

分层说明：
- 应用层通过 create_tooling(register_defaults=True) 得到 registry/executor 并注入 Agent。
- 业务工具应继承 BaseTool，并通过 registry.register(...) 显式注册。
- 默认工具（时间、加法、HTTP）在 tools/catalog/defaults.py 中以 BaseTool 子类实现。
"""
from __future__ import annotations

from typing import Any, Optional

from ..registry.registry import ToolRegistry
from ..runtime.executor import ToolExecutor

_default_registry: Optional[ToolRegistry] = None
_default_executor: Optional[ToolExecutor] = None


def create_tooling(*, register_defaults: bool = True) -> tuple[ToolRegistry, ToolExecutor]:
    """创建工具注册表与执行器；register_defaults=True 时注册框架默认工具（时间、加法、HTTP）。"""
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    if register_defaults:
        from ..catalog.defaults import register_default_tools
        register_default_tools(registry)
    return registry, executor


def _get_default_registry() -> ToolRegistry:
    global _default_registry, _default_executor
    if _default_registry is None:
        _default_registry, _default_executor = create_tooling(register_defaults=True)
    return _default_registry


def _get_default_executor() -> ToolExecutor:
    global _default_registry, _default_executor
    if _default_executor is None:
        _default_registry, _default_executor = create_tooling(register_defaults=True)
    return _default_executor


# 向后兼容：from tools import tool_registry / tool_executor 时懒加载
def __getattr__(name: str) -> Any:
    if name == "tool_registry":
        return _get_default_registry()
    if name == "tool_executor":
        return _get_default_executor()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
