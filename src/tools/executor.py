from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import ToolResult
from .context import ToolContext
from .registry import ToolRegistry

logger = logging.getLogger(__name__)

try:
    from ..config import TOOL_CONFIG
except ImportError:
    TOOL_CONFIG = {"max_retries": 2}


def _tool_error_retryable(exc: BaseException) -> bool:
    """工具执行异常是否可重试：超时、连接、5xx。"""
    msg = str(exc).lower()
    if "timeout" in msg or "timed out" in msg or "connection" in msg or "connect" in msg:
        return True
    if "50" in msg or "502" in msg or "503" in msg or "504" in msg:
        return True
    return False


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
        self._max_retries = TOOL_CONFIG.get("max_retries", 2)

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
            logger.error("tool_not_found tool_name=%s", tool_name)
            return ToolExecution(
                tool_name=tool_name,
                arguments=arguments,
                result=ToolResult(ok=False, content="", error=f"工具不存在: {tool_name}"),
                tool_call_id=tool_call_id,
            )

        args_summary = json.dumps(arguments, ensure_ascii=False)[:200]
        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                result = tool.execute(arguments, context)
                logger.info(
                    "tool_exec tool_name=%s ok=%s args_summary=%s retried=%s",
                    tool_name,
                    result.ok,
                    args_summary,
                    attempt > 0,
                )
                if attempt > 0 and result.ok:
                    result.metadata = dict(result.metadata or {}, _retried=attempt)
                if not result.ok:
                    logger.error(
                        "tool_exec_failed tool_name=%s error=%s",
                        tool_name,
                        result.error,
                    )
                return ToolExecution(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                    tool_call_id=tool_call_id,
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                logger.error(
                    "tool_exec_exception tool_name=%s attempt=%s exception=%s",
                    tool_name,
                    attempt + 1,
                    str(exc),
                )
                if attempt == self._max_retries or not _tool_error_retryable(exc):
                    return ToolExecution(
                        tool_name=tool_name,
                        arguments=arguments,
                        result=ToolResult(ok=False, content="", error=str(exc)),
                        tool_call_id=tool_call_id,
                    )
                time.sleep(0.5 * (attempt + 1))
        return ToolExecution(
            tool_name=tool_name,
            arguments=arguments,
            result=ToolResult(ok=False, content="", error=str(last_exc)),
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

