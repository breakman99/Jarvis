"""
AgentCoordinator：多 Agent 编排与路由。
"""
from __future__ import annotations

from typing import Optional

from ..tools import ToolContext
from .base_agent import BaseAgent
from .memory import MemoryService
from .response import AgentResponse
from .router import AgentRouter, DefaultRouter
from .session import AgentSession


class AgentCoordinator:
    """负责 memory 更新、agent 路由、会话管理与单次请求编排。"""

    def __init__(
        self,
        *,
        agents: list[BaseAgent],
        router: AgentRouter | None = None,
        memory_service: MemoryService | None = None,
        default_agent_name: str | None = None,
    ):
        if not agents:
            raise ValueError("AgentCoordinator 至少需要一个 Agent")
        self._agents = {agent.name: agent for agent in agents}
        self._default_agent_name = default_agent_name or agents[0].name
        self._router: AgentRouter = router or DefaultRouter(self._default_agent_name)
        self._memory_service = memory_service
        self._last_session: AgentSession | None = None

    @property
    def last_session(self) -> Optional[AgentSession]:
        return self._last_session

    def _build_system_prompt(self, agent: BaseAgent) -> str:
        prompt = agent.system_prompt
        if self._memory_service:
            hint = self._memory_service.build_system_context()
            if hint:
                prompt = f"{prompt}\n\n已知用户记忆: {hint}"
        return prompt

    def run(
        self,
        user_input: str,
        *,
        context: ToolContext | None = None,
        session: AgentSession | None = None,
    ) -> AgentResponse:
        active_context = context or ToolContext.create()
        if self._memory_service:
            self._memory_service.observe_user_input(user_input)

        target_name = self._router.route(user_input, active_context)
        agent = self._agents.get(target_name)
        if agent is None:
            raise ValueError(f"未找到目标 Agent: {target_name}")

        if session is None:
            active_session = AgentSession(system_prompt=self._build_system_prompt(agent))
        else:
            active_session = session
            active_session.refresh_system_prompt(self._build_system_prompt(agent))
        response = agent.run(user_input, context=active_context, session=active_session)
        self._last_session = active_session
        return response
