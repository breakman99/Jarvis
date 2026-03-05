from __future__ import annotations

from typing import Any

from ...spec.base import BaseTool, ToolResult, ToolSpec


class AddNumbersTool(BaseTool):
    """两数相加。"""

    def __init__(self) -> None:
        super().__init__(
            ToolSpec(
                name="add_numbers",
                description="加法计算器。当用户需要计算两个数字之和时使用。",
                parameters={
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "第一个加数"},
                        "b": {"type": "number", "description": "第二个加数"},
                    },
                    "required": ["a", "b"],
                },
                idempotent=True,
            )
        )

    def execute(self, args: dict[str, Any], context: Any | None = None) -> ToolResult:
        _ = context
        a = args.get("a", 0)
        b = args.get("b", 0)
        try:
            return ToolResult(ok=True, content=str(float(a) + float(b)))
        except (TypeError, ValueError) as exc:
            return ToolResult(ok=False, content="", error=str(exc))
