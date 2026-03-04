"""
Orchestrator：驱动多轮 LLM + 工具循环，负责单次请求内的执行与工具编排。

不承担规划职责；输入为 user_input、可选的 RequestContext 与 AgentSession，
通过 engine.chat(messages, tools) 获取模型决策，若有 tool_calls 则经 ToolExecutor
执行并写回 tool 消息后继续循环，直到返回最终文本或达到最大迭代次数。
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import List, Optional

from ..engine import LLMEngineProtocol
from ..observability import metrics
from ..tools import ToolContext, ToolExecutor, ToolRegistry
from .memory import MemoryService
from .response import AgentResponse
from .session import AgentSession

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "你是一个严谨的助手。请善用工具回答问题。"


@dataclass
class AgentOrchestratorConfig:
    """Orchestrator 运行参数：最大迭代轮数、系统提示词。"""
    max_iterations: int = 5
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


class AgentOrchestrator:
    """单次请求的 LLM + 工具循环执行器；由 ConversationAgent 委托调用。"""

    def __init__(
        self,
        *,
        engine: LLMEngineProtocol,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        config: Optional[AgentOrchestratorConfig] = None,
        memory_service: Optional[MemoryService] = None,
    ):
        self.engine = engine
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.config = config or AgentOrchestratorConfig()
        self.memory_service = memory_service

    def run(
        self,
        user_input: str,
        *,
        context: Optional[ToolContext] = None,
        session: Optional[AgentSession] = None,
    ) -> AgentResponse:
        """
        执行一轮（或多轮）对话：若未传入 session 则用 memory 构建 system_prompt 并创建新 session；
        循环调用 engine.chat，无 tool_calls 时返回最终 content，有则执行工具并继续，直到结束或超时/取消/达到 max_iterations。
        """
        active_context = context or ToolContext.create(session_id=uuid.uuid4().hex)
        should_observe_memory = not bool(active_context.extra.get("memory_observed"))
        if self.memory_service and should_observe_memory:
            self.memory_service.observe_user_input(user_input)
        if session is None:
            prompt = self.config.system_prompt
            if self.memory_service:
                memory_hint = self.memory_service.build_system_context()
                if memory_hint:
                    prompt = f"{prompt}\n\n已知用户记忆: {memory_hint}"
            active = AgentSession(system_prompt=prompt)
        else:
            active = session
        active.append_user(user_input)
        phase_log: List[str] = []
        metrics.inc("orchestrator_runs_total", labels={"mode": "single" if session is None else "shared"})

        for iteration in range(self.config.max_iterations):
            if active_context.should_stop():
                return AgentResponse(
                    content="请求已取消或超时，任务已停止。",
                    metadata={"reason": "deadline_or_cancelled", "phase_log": phase_log},
                    steps=[],
                )
            logger.debug(
                "iteration=%s messages_count=%s",
                iteration + 1,
                len(active.messages),
            )
            response = self.engine.chat(
                active.messages,
                tools=self.tool_registry.to_openai_tools(),
                context=active_context,
            )
            if not response.tool_calls:
                logger.info(
                    "event=orchestrator_decision iteration=%s decision=final_answer request_id=%s trace_id=%s",
                    iteration + 1,
                    active_context.request_id,
                    active_context.trace_id,
                )
                if iteration == 0:
                    phase_log.extend(["think", "plan", "review"])
                else:
                    phase_log.append("review")
                content = response.content or ""
                active.append_assistant(content)
                logger.info("finished_with=success")
                return AgentResponse(
                    content=content,
                    steps=[],
                    metadata={
                        "phase_log": phase_log,
                        "request_id": active_context.request_id,
                        "trace_id": active_context.trace_id,
                    },
                )

            tool_names = [tc.name for tc in response.tool_calls]
            logger.info(
                "event=orchestrator_decision iteration=%s decision=use_tools tools=%s request_id=%s trace_id=%s",
                iteration + 1,
                tool_names,
                active_context.request_id,
                active_context.trace_id,
            )
            if iteration == 0:
                phase_log.extend(["think", "plan", "act"])
            else:
                phase_log.append("act")
            tool_calls_payload = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": call.arguments,
                    },
                }
                for call in response.tool_calls
            ]
            active.append_assistant_tool_calls_data(response.content or "", tool_calls_payload)
            for tool_call in response.tool_calls:
                execution = self.tool_executor.execute_tool_call(tool_call, context=active_context)
                active.append_tool_message(execution.to_tool_message())
            metrics.inc("orchestrator_iterations", labels={"status": "continued"})

        logger.info("finished_with=max_iterations")
        return AgentResponse(
            content="达到最大任务循环次数, Agent 未能完成任务。",
            metadata={"reason": "max_iterations_reached", "phase_log": phase_log},
            steps=[],
        )

