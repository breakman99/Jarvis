from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.domain.common.request_context import ToolContext
from src.domain.common.observability import metrics
from src.domain.ports import LLMEngineProtocol
from src.domain.tools.runtime.executor import ToolExecutor
from ..models.response import AgentResponse
from ..models.session import AgentSession
from ..runtime.tool_set import ToolSet

logger = logging.getLogger(__name__)


@dataclass
class LoopExecutorConfig:
    max_iterations: int = 5
    max_consecutive_tool_failures: int = 3
    enable_session_trim: bool = False
    max_session_messages: int = 80


@dataclass
class ExecutionResult:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ExecutorProtocol(Protocol):
    def execute(
        self,
        user_input: str,
        *,
        tools: ToolSet,
        session: AgentSession,
        context: ToolContext | None = None,
        steps: list[str] | None = None,
    ) -> ExecutionResult:
        ...


class LoopExecutor:
    """LLM + Tool 循环执行策略，不承担 memory/session 构建职责。"""

    def __init__(
        self,
        *,
        engine: LLMEngineProtocol,
        tool_executor: ToolExecutor,
        config: LoopExecutorConfig | None = None,
    ):
        self._engine = engine
        self._tool_executor = tool_executor
        self._config = config or LoopExecutorConfig()

    def execute(
        self,
        user_input: str,
        *,
        tools: ToolSet,
        session: AgentSession,
        context: ToolContext | None = None,
        steps: list[str] | None = None,
    ) -> ExecutionResult:
        _ = user_input, steps
        active_context = context or ToolContext.create()
        if self._config.enable_session_trim:
            session.trim(max_messages=self._config.max_session_messages)

        phase_log: list[str] = []
        tool_traces: list[dict[str, Any]] = []
        consecutive_tool_failures = 0
        metrics.inc("orchestrator_runs_total", labels={"mode": "shared"})

        for iteration in range(self._config.max_iterations):
            if active_context.should_stop():
                return ExecutionResult(
                    content="请求已取消或超时，任务已停止。",
                    metadata={
                        "reason": "deadline_or_cancelled",
                        "phase_log": phase_log,
                        "tool_traces": tool_traces,
                        "request_id": active_context.request_id,
                        "trace_id": active_context.trace_id,
                    },
                )
            response = self._engine.chat(
                session.messages,
                tools=tools.to_openai_tools(),
                context=active_context,
            )
            if not response.tool_calls:
                if iteration == 0:
                    phase_log.extend(["think", "plan", "review"])
                else:
                    phase_log.append("review")
                content = response.content or ""
                session.append_assistant(content)
                return ExecutionResult(
                    content=content,
                    metadata={
                        "phase_log": phase_log,
                        "tool_traces": tool_traces,
                        "request_id": active_context.request_id,
                        "trace_id": active_context.trace_id,
                    },
                )

            if iteration == 0:
                phase_log.extend(["think", "plan", "act"])
            else:
                phase_log.append("act")
            tool_calls_payload = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in response.tool_calls
            ]
            session.append_assistant_tool_calls_data(response.content or "", tool_calls_payload)
            for tool_call in response.tool_calls:
                execution = self._tool_executor.execute_tool_call(tool_call, context=active_context)
                session.append_tool_message(execution.to_tool_message())
                tool_traces.append(
                    {
                        "tool_name": execution.tool_name,
                        "tool_call_id": execution.tool_call_id or "",
                        "ok": execution.result.ok,
                        "error": execution.result.error or "",
                        "retried": int(execution.result.metadata.get("_retried", 0)),
                    }
                )
                if execution.result.ok:
                    consecutive_tool_failures = 0
                else:
                    consecutive_tool_failures += 1
                if self._config.enable_session_trim:
                    session.trim(max_messages=self._config.max_session_messages)
                if consecutive_tool_failures >= self._config.max_consecutive_tool_failures:
                    logger.warning(
                        "event=loop_executor_stop reason=consecutive_tool_failures count=%s request_id=%s trace_id=%s",
                        consecutive_tool_failures,
                        active_context.request_id,
                        active_context.trace_id,
                    )
                    session.messages.append(
                        {
                            "role": "system",
                            "content": (
                                "工具已连续失败，停止继续调用工具。"
                                "请基于当前对话与已获取信息，输出最终结论，"
                                "并明确失败原因与可执行的替代方案。"
                            ),
                        }
                    )
                    final_response = self._engine.chat(
                        session.messages,
                        tools=None,
                        context=active_context,
                    )
                    final_content = (
                        final_response.content
                        or "工具连续失败，且无法生成稳定结论。请稍后重试或更换数据源。"
                    )
                    session.append_assistant(final_content)
                    phase_log.append("review")
                    return ExecutionResult(
                        content=final_content,
                        metadata={
                            "reason": "consecutive_tool_failures_finalized",
                            "phase_log": phase_log,
                            "tool_traces": tool_traces,
                            "request_id": active_context.request_id,
                            "trace_id": active_context.trace_id,
                        },
                    )
            metrics.inc("orchestrator_iterations", labels={"status": "continued"})

        return ExecutionResult(
            content="达到最大任务循环次数, Agent 未能完成任务。",
            metadata={
                "reason": "max_iterations_reached",
                "phase_log": phase_log,
                "tool_traces": tool_traces,
                "request_id": active_context.request_id,
                "trace_id": active_context.trace_id,
            },
        )


def to_agent_response(result: ExecutionResult, steps: list[str] | None = None) -> AgentResponse:
    return AgentResponse(
        content=result.content,
        steps=steps or [],
        metadata=result.metadata,
    )
