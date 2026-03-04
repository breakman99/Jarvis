from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .base import BaseTool, FunctionTool, ToolSpec


class ToolRegistry:
    """
    工具注册中心：维护 name -> BaseTool 映射，并导出 OpenAI 风格 tools schema。

    设计意图：Agent 只需从本注册表获取 to_openai_tools() 传给 LLM，新增工具只需
    在此注册，无需改 Orchestrator。协作：ToolExecutor 通过 registry.get(name) 取
    工具并执行；builtin 工具由应用装配阶段显式注册。
    """

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
        idempotent: bool = False,
        func: Callable[..., Any],
    ) -> BaseTool:
        tool = FunctionTool(
            spec=ToolSpec(
                name=name,
                description=description,
                parameters=parameters,
                idempotent=idempotent,
            ),
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
        idempotent: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.register_function(
                name=name or func.__name__,
                description=description,
                parameters=parameters,
                idempotent=idempotent,
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

