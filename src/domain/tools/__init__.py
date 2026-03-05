from .base import BaseTool, FunctionTool, ToolResult, ToolSpec
from .context import ToolContext, RequestContext
from .executor import ToolExecution, ToolExecutor
from .factory import create_tooling, tool
from .registry import ToolRegistry

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
        from . import factory
        return getattr(factory, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
