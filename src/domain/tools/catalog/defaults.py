"""
框架默认工具：以 BaseTool 子类实现，由 create_tooling(register_defaults=True) 或 register_default_tools(registry) 注册。

分层：本模块仅负责默认工具装配；每个默认工具类位于 builtin 子目录独立文件。
"""
from __future__ import annotations

from ..registry.registry import ToolRegistry
from .builtin import AddNumbersTool, GetCurrentTimeTool, HttpGetTool, HttpPostJsonTool


DEFAULT_TOOL_CLASSES = (
    GetCurrentTimeTool,
    AddNumbersTool,
    HttpGetTool,
    HttpPostJsonTool,
)


def register_default_tools(registry: ToolRegistry) -> None:
    """将框架默认工具（时间、加法、HTTP GET/POST）注册到给定 registry；重复调用会因重名而抛错，由调用方保证只注册一次。"""
    for cls in DEFAULT_TOOL_CLASSES:
        instance = cls()
        if not registry.has(instance.name):
            registry.register(instance)
