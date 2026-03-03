from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import ToolResult
from .context import ToolContext
from .registry import ToolRegistry


@dataclass
class ToolExecution:
    tool_name: str
    arguments: Dict[str, Any]
    result: ToolResult
    tool_call_id: Optional[str] = None

    def to_tool_message(self) -> Dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "name": self.tool_name,
            "content": self.result.to_message_content(),
        }


class ToolExecutor:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[ToolContext] = None,
        *,
        tool_call_id: Optional[str] = None,
    ) -> ToolExecution:
        tool = self.registry.get(tool_name)
        if tool is None:
            return ToolExecution(
                tool_name=tool_name,
                arguments=arguments,
                result=ToolResult(ok=False, content="", error=f"工具不存在: {tool_name}"),
                tool_call_id=tool_call_id,
            )

        try:
            result = tool.execute(arguments, context)
            return ToolExecution(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                tool_call_id=tool_call_id,
            )
        except Exception as exc:  # noqa: BLE001
            return ToolExecution(
                tool_name=tool_name,
                arguments=arguments,
                result=ToolResult(ok=False, content="", error=str(exc)),
                tool_call_id=tool_call_id,
            )

    def execute_tool_call(
        self, tool_call: Any, context: Optional[ToolContext] = None
    ) -> ToolExecution:
        tool_name = tool_call.function.name
        raw_args = tool_call.function.arguments or "{}"
        arguments = json.loads(raw_args)
        return self.execute(
            tool_name=tool_name,
            arguments=arguments,
            context=context,
            tool_call_id=getattr(tool_call, "id", None),
        )

