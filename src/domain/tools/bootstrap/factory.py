"""
工具层装配入口：create_tooling() 创建 ToolRegistry + ToolExecutor，可选注册默认工具。

分层说明：
- 应用层通过 create_tooling(register_defaults=True) 得到 registry/executor 并注入 Agent。
- 业务工具应继承 BaseTool，并通过 registry.register(...) 显式注册。
- 默认工具（时间、加法、HTTP）在 tools/catalog/defaults.py 中以 BaseTool 子类实现。
"""
from __future__ import annotations

from ..registry.registry import ToolRegistry
from ..runtime.executor import ToolExecutor

def create_tooling(*, register_defaults: bool = True) -> tuple[ToolRegistry, ToolExecutor]:
    """创建工具注册表与执行器；register_defaults=True 时注册框架默认工具（时间、加法、HTTP）。"""
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    if register_defaults:
        from ..catalog.defaults import register_default_tools
        register_default_tools(registry)
    return registry, executor
