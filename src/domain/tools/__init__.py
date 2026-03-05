from .bootstrap import create_tooling, tool
from .registry import ToolRegistry
from .runtime import RequestContext, ToolContext, ToolExecution, ToolExecutor
from .spec import BaseTool, FunctionTool, ToolResult, ToolSpec

__all__ = [
    "BaseTool",
    "FunctionTool",
    "ToolSpec",
    "ToolResult",
    "ToolRegistry",
    "ToolContext",
    "RequestContext",
    "ToolExecution",
    "ToolExecutor",
    "create_tooling",
    "tool",
]


def __getattr__(name: str):
    if name in ("tool_registry", "tool_executor"):
        from .bootstrap import factory

        return getattr(factory, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
