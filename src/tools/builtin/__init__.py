"""
内置工具：时间、加法、HTTP GET/POST 等，通过 register_builtin_tools(registry) 注册。

由 bootstrap.create_tooling(register_builtin=True) 在应用启动时调用，无需改编排代码即可使用。
"""
from . import http
from .basic import add_numbers, get_current_time


def register_builtin_tools(registry) -> None:
    """将 basic 与 http 模块中的工具注册到给定 registry；重复调用时由各模块内部做 has 检查。"""
    from . import basic
    basic.register_tools(registry)
    http.register_tools(registry)


__all__ = ["get_current_time", "add_numbers", "register_builtin_tools"]

