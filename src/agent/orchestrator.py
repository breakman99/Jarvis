"""
Orchestrator：驱动多轮 LLM+工具 循环，实现 Think/Plan/Act/Review 轻量阶段化。

通过 system prompt（Planner 注入）引导模型按阶段回复；在 metadata.phase_log 中记录
所经历的阶段，便于观测与后续演进为显式状态机。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from ..engine import LLMGateway

logger = logging.getLogger(__name__)
from ..tools import ToolContext, ToolExecutor, ToolRegistry
from .memory import MemoryService
from .planner import Planner
from .response import AgentResponse
from .session import AgentSession


DEFAULT_SYSTEM_PROMPT = "你是一个严谨的助手。请善用工具回答问题。"


@dataclass
class AgentOrchestratorConfig:
    max_iterations: int = 5
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


class AgentOrchestrator:
    def __init__(
        self,
        *,
        engine: LLMGateway,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        config: Optional[AgentOrchestratorConfig] = None,
        planner: Optional[Planner] = None,
        memory_service: Optional[MemoryService] = None,
    ):
        self.engine = engine
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self.config = config or AgentOrchestratorConfig()
        self.planner = planner or Planner(enabled=False)
        self.memory_service = memory_service

        prompt = self.config.system_prompt
        hint = self.planner.planning_hint()
        if hint:
            prompt = f"{prompt}\n\n{hint}"
        if self.memory_service:
            memory_hint = self.memory_service.build_system_context()
            if memory_hint:
                prompt = f"{prompt}\n\n已知用户记忆: {memory_hint}"
        self.session = AgentSession(system_prompt=prompt)

    def run(self, user_input: str, *, context: Optional[ToolContext] = None) -> AgentResponse:
        if self.memory_service:
            self.memory_service.observe_user_input(user_input)
        self.session.append_user(user_input)
        steps = self.planner.plan_steps(user_input)
        phase_log: List[str] = []

        for iteration in range(self.config.max_iterations):
            logger.debug(
                "iteration=%s messages_count=%s",
                iteration + 1,
                len(self.session.messages),
            )
            response = self.engine.chat(
                self.session.messages,
                tools=self.tool_registry.to_openai_tools(),
            )
            resp_msg = response.choices[0].message
            if not resp_msg.tool_calls:
                logger.info(
                    "iteration=%s decision=final_answer",
                    iteration + 1,
                )
                if iteration == 0:
                    phase_log.extend(["think", "plan", "review"])
                else:
                    phase_log.append("review")
                content = resp_msg.content or ""
                self.session.append_assistant(content)
                logger.info("finished_with=success")
                return AgentResponse(
                    content=content,
                    steps=steps,
                    metadata={"phase_log": phase_log},
                )

            tool_names = [tc.function.name for tc in resp_msg.tool_calls]
            logger.info(
                "iteration=%s decision=use_tools tools=%s",
                iteration + 1,
                tool_names,
            )
            if iteration == 0:
                phase_log.extend(["think", "plan", "act"])
            else:
                phase_log.append("act")
            self.session.append_assistant_tool_calls(resp_msg)
            for tool_call in resp_msg.tool_calls:
                execution = self.tool_executor.execute_tool_call(tool_call, context=context)
                self.session.append_tool_message(execution.to_tool_message())

        logger.info("finished_with=max_iterations")
        return AgentResponse(
            content="达到最大任务循环次数, Agent 未能完成任务。",
            metadata={"reason": "max_iterations_reached", "phase_log": phase_log},
            steps=steps,
        )

