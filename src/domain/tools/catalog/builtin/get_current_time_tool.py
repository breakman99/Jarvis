from __future__ import annotations

import datetime
from typing import Any

from ...spec.base import BaseTool, ToolResult, ToolSpec


class GetCurrentTimeTool(BaseTool):
    """获取当前本地时间。"""

    def __init__(self) -> None:
        super().__init__(
            ToolSpec(
                name="get_current_time",
                description="获取当前时间。用于回答时间、日期相关问题。",
                parameters={"type": "object", "properties": {}},
                idempotent=True,
            )
        )

    def execute(self, args: dict[str, Any], context: Any | None = None) -> ToolResult:
        _ = args, context
        s = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return ToolResult(ok=True, content=s)
