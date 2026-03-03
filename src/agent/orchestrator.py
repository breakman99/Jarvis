from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..engine import LLMGateway
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

        for _ in range(self.config.max_iterations):
            response = self.engine.chat(
                self.session.messages,
                tools=self.tool_registry.to_openai_tools(),
            )
            resp_msg = response.choices[0].message
            if not resp_msg.tool_calls:
                content = resp_msg.content or ""
                self.session.append_assistant(content)
                return AgentResponse(content=content, steps=steps)

            self.session.append_assistant_tool_calls(resp_msg)
            for tool_call in resp_msg.tool_calls:
                execution = self.tool_executor.execute_tool_call(tool_call, context=context)
                self.session.append_tool_message(execution.to_tool_message())

        return AgentResponse(
            content="达到最大任务循环次数, Agent 未能完成任务。",
            metadata={"reason": "max_iterations_reached"},
            steps=steps,
        )

