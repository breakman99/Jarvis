"""
工具执行器：根据 registry 查找工具、解析参数、执行并归一化结果为 ToolExecution。

支持可配置重试（仅对 idempotent 工具）、超时/取消检查（RequestContext.should_stop）；
异常统一转为 ToolResult(ok=False)，并打点 metrics、发送 audit 事件。
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.infrastructure.common import CancelledError, TimeoutError
from src.infrastructure.llm.types import LLMToolCall
from src.infrastructure.observability import emit_audit_event, metrics
from .base import ToolResult
from .context import RequestContext, ToolContext
from .registry import ToolRegistry

logger = logging.getLogger(__name__)

try:
    from src.infrastructure.config import TOOL_CONFIG
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
    """单次工具调用的完整记录：工具名、参数、执行结果、tool_call_id；可转为 role=tool 消息。"""
    tool_name: str
    arguments: Dict[str, Any]
    result: ToolResult
    tool_call_id: Optional[str] = None

    def to_tool_message(self) -> Dict[str, Any]:
        """转为 OpenAI 格式的 role=tool 消息，供 session 追加。"""
        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "name": self.tool_name,
            "content": self.result.to_message_content(),
        }


class ToolExecutor:
    """统一执行工具调用：get 工具、执行、捕获异常为 ToolResult；可选重试与 context 超时/取消。"""
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._max_retries = TOOL_CONFIG.get("max_retries", 2)

    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[RequestContext] = None,
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
        max_attempts = self._max_retries + 1 if tool.spec.idempotent else 1
        for attempt in range(self._max_retries + 1):
            if attempt >= max_attempts:
                break
            if context and context.should_stop():
                err = CancelledError() if context.cancelled else TimeoutError("tool deadline exceeded")
                return ToolExecution(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=ToolResult(ok=False, content="", error=str(err)),
                    tool_call_id=tool_call_id,
                )
            start = time.perf_counter()
            try:
                result = tool.execute(arguments, context)
                latency_ms = (time.perf_counter() - start) * 1000.0
                logger.info(
                    "event=tool_exec tool_name=%s ok=%s args_summary=%s retried=%s request_id=%s trace_id=%s latency_ms=%.0f",
                    tool_name,
                    result.ok,
                    args_summary,
                    attempt > 0,
                    context.request_id if context else "",
                    context.trace_id if context else "",
                    latency_ms,
                )
                metrics.inc(
                    "tool_calls_total",
                    labels={"tool": tool_name, "status": "ok" if result.ok else "error"},
                )
                metrics.observe("tool_call_latency_ms", latency_ms, labels={"tool": tool_name})
                if attempt > 0 and result.ok:
                    result.metadata = dict(result.metadata or {}, _retried=attempt)
                if not result.ok:
                    logger.error(
                        "event=tool_exec_failed tool_name=%s error=%s request_id=%s trace_id=%s",
                        tool_name,
                        result.error,
                        context.request_id if context else "",
                        context.trace_id if context else "",
                    )
                emit_audit_event(
                    "tool_execution",
                    actor="ToolExecutor",
                    context=context,
                    payload={"tool_name": tool_name, "ok": result.ok},
                    status="ok" if result.ok else "error",
                )
                return ToolExecution(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                    tool_call_id=tool_call_id,
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                latency_ms = (time.perf_counter() - start) * 1000.0
                logger.error(
                    "event=tool_exec_exception tool_name=%s attempt=%s exception=%s request_id=%s trace_id=%s latency_ms=%.0f",
                    tool_name,
                    attempt + 1,
                    str(exc),
                    context.request_id if context else "",
                    context.trace_id if context else "",
                    latency_ms,
                )
                metrics.inc("tool_calls_total", labels={"tool": tool_name, "status": "error"})
                metrics.observe("tool_call_latency_ms", latency_ms, labels={"tool": tool_name})
                if attempt == max_attempts - 1 or not _tool_error_retryable(exc):
                    emit_audit_event(
                        "tool_execution",
                        actor="ToolExecutor",
                        context=context,
                        payload={"tool_name": tool_name, "error": str(exc)},
                        status="error",
                    )
                    return ToolExecution(
                        tool_name=tool_name,
                        arguments=arguments,
                        result=ToolResult(ok=False, content="", error=str(exc)),
                        tool_call_id=tool_call_id,
                    )
                metrics.inc("retry_total", labels={"layer": "tool", "reason": type(exc).__name__})
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
        if isinstance(tool_call, LLMToolCall):
            tool_name = tool_call.name
            raw_args = tool_call.arguments or "{}"
            tool_call_id = tool_call.id
        else:
            tool_name = tool_call.function.name
            raw_args = tool_call.function.arguments or "{}"
            tool_call_id = getattr(tool_call, "id", None)
        try:
            arguments = json.loads(raw_args)
            if not isinstance(arguments, dict):
                raise ValueError("tool arguments must be a JSON object")
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "event=tool_args_invalid tool_name=%s error=%s request_id=%s trace_id=%s",
                tool_name,
                str(exc),
                context.request_id if context else "",
                context.trace_id if context else "",
            )
            return ToolExecution(
                tool_name=tool_name,
                arguments={},
                result=ToolResult(ok=False, content="", error=f"工具参数解析失败: {exc}"),
                tool_call_id=tool_call_id,
            )
        return self.execute(
            tool_name=tool_name,
            arguments=arguments,
            context=context,
            tool_call_id=tool_call_id,
        )
