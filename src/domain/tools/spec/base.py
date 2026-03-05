"""
工具层基础类型：ToolSpec（描述）、ToolResult（执行结果）、BaseTool / FunctionTool（实现）。

与 OpenAI function calling 对接：ToolSpec.to_openai_schema() 产出 type/function 结构；
ToolResult.to_message_content() 产出供 role=tool 的 content 文本。
"""
from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass(frozen=True)
class ToolSpec:
    """工具描述：name、description、parameters（JSON Schema）、是否幂等（用于重试策略）。"""
    name: str
    description: str
    parameters: Dict[str, Any]
    idempotent: bool = False

    def to_openai_schema(self) -> Dict[str, Any]:
        """转换为 OpenAI function calling 所需的 type/function 结构。"""
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
    """单次工具执行结果：成功时 content 为返回值文本，失败时 error 为原因；可带 metadata。"""
    ok: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_message_content(self) -> str:
        """转为供 LLM 的 role=tool 消息 content：成功即 content，失败为「工具执行失败: error」。"""
        if self.ok:
            return self.content
        return f"工具执行失败: {self.error or '未知错误'}"


class BaseTool(ABC):
    """工具抽象：持有 ToolSpec，执行 execute(args, context?) -> ToolResult。"""
    def __init__(self, spec: ToolSpec):
        self.spec = spec

    @property
    def name(self) -> str:
        return self.spec.name

    @abstractmethod
    def execute(self, args: Dict[str, Any], context: Optional[Any] = None) -> ToolResult:
        raise NotImplementedError


class FunctionTool(BaseTool):
    """将 Python 函数适配为 BaseTool：参数从 args 映射，若函数签名含 context 则注入。"""
    def __init__(self, spec: ToolSpec, func: Callable[..., Any]):
        super().__init__(spec)
        self._func = func
        self._signature = inspect.signature(func)

    def execute(self, args: Dict[str, Any], context: Optional[Any] = None) -> ToolResult:
        kwargs = dict(args)
        if "context" in self._signature.parameters:
            kwargs["context"] = context
        result = self._func(**kwargs)
        if isinstance(result, ToolResult):
            return result
        return ToolResult(ok=True, content=str(result))
