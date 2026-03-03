from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .base import BaseTool, FunctionTool, ToolSpec


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"工具已存在: {tool.name}")
        self._tools[tool.name] = tool

    def register_function(
        self,
        *,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        func: Callable[..., Any],
    ) -> BaseTool:
        tool = FunctionTool(
            spec=ToolSpec(name=name, description=description, parameters=parameters),
            func=func,
        )
        self.register(tool)
        return tool

    def tool(
        self,
        *,
        name: Optional[str] = None,
        description: str,
        parameters: Dict[str, Any],
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.register_function(
                name=name or func.__name__,
                description=description,
                parameters=parameters,
                func=func,
            )
            return func

        return decorator

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def to_openai_tools(self) -> List[Dict[str, Any]]:
        return [tool.spec.to_openai_schema() for tool in self.list_tools()]

