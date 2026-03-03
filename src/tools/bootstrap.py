from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .executor import ToolExecutor
from .registry import ToolRegistry

tool_registry = ToolRegistry()
tool_executor = ToolExecutor(tool_registry)


def tool(
    *,
    name: Optional[str] = None,
    description: str,
    parameters: Dict[str, Any],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    return tool_registry.tool(name=name, description=description, parameters=parameters)

