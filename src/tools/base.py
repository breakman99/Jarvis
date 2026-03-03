from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
import inspect


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]

    def to_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolResult:
    ok: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_message_content(self) -> str:
        if self.ok:
            return self.content
        return f"工具执行失败: {self.error or '未知错误'}"


class BaseTool(ABC):
    def __init__(self, spec: ToolSpec):
        self.spec = spec

    @property
    def name(self) -> str:
        return self.spec.name

    @abstractmethod
    def execute(self, args: Dict[str, Any], context: Optional[Any] = None) -> ToolResult:
        raise NotImplementedError


class FunctionTool(BaseTool):
    def __init__(self, spec: ToolSpec, func: Callable[..., Any]):
        super().__init__(spec)
        self._func = func
        self._signature = inspect.signature(func)

    def execute(self, args: Dict[str, Any], context: Optional[Any] = None) -> ToolResult:
        kwargs = dict(args)
        if "context" in self._signature.parameters:
            kwargs["context"] = context

        result = self._func(**kwargs)
        return ToolResult(ok=True, content=str(result))

