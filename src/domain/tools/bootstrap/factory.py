"""
工具层装配入口：create_tooling() 创建 ToolRegistry + ToolExecutor，可选注册默认工具。

分层说明：
- 应用层通过 create_tooling(register_defaults=True) 得到 registry/executor 并注入 Agent。
- 业务工具应继承 BaseTool，并通过 registry.register(...) 显式注册。
- 默认工具（时间、加法、HTTP）在 tools/catalog/defaults.py 中以 BaseTool 子类实现。
"""
from __future__ import annotations

from typing import Any

from ..registry.registry import ToolRegistry
from ..runtime.executor import ToolExecutor

def create_tooling(
    *,
    register_defaults: bool = True,
    max_retries: int = 2,
    http_allow_hosts: Any = None,
    http_deny_hosts: Any = None,
) -> tuple[ToolRegistry, ToolExecutor]:
    """创建工具注册表与执行器；register_defaults=True 时注册框架默认工具（时间、加法、HTTP）。"""
    registry = ToolRegistry()
    executor = ToolExecutor(registry, max_retries=max_retries)
    if register_defaults:
        from ..catalog.defaults import register_default_tools
        register_default_tools(
            registry,
            http_allow_hosts=http_allow_hosts,
            http_deny_hosts=http_deny_hosts,
        )
    return registry, executor
