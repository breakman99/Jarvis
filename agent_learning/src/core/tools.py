from __future__ import annotations

import ast
import datetime as dt
from dataclasses import dataclass
from typing import Any, Callable


class ToolError(Exception):
    pass


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], str]

    def run(self, arguments: dict[str, Any]) -> str:
        try:
            return self.handler(arguments)
        except Exception as exc:  # noqa: BLE001
            raise ToolError(f"Tool {self.name} failed: {exc}") from exc

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolError(f"Tool {name} not found.")
        return self._tools[name]

    def run(self, name: str, arguments: dict[str, Any]) -> str:
        return self.get(name).run(arguments)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)


def _safe_eval_math(expr: str) -> float:
    allowed_ops = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.Mod)

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_eval(node.operand)
        if isinstance(node, ast.BinOp) and isinstance(node.op, allowed_ops):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                return left**right
            if isinstance(node.op, ast.Mod):
                return left % right
        raise ValueError("Unsupported expression.")

    tree = ast.parse(expr, mode="eval")
    return _eval(tree)


def build_default_tools() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        Tool(
            name="get_time",
            description="Get current local time in ISO format.",
            parameters={
                "type": "object",
                "properties": {},
                "required": [],
            },
            handler=lambda _: dt.datetime.now().isoformat(timespec="seconds"),
        )
    )
    registry.register(
        Tool(
            name="calculator",
            description="Evaluate a simple math expression.",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression"}
                },
                "required": ["expression"],
            },
            handler=lambda args: str(_safe_eval_math(str(args["expression"]))),
        )
    )
    registry.register(
        Tool(
            name="echo",
            description="Echo the provided text.",
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
            handler=lambda args: str(args["text"]),
        )
    )
    return registry
