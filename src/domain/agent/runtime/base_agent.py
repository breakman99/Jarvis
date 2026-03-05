"""
BaseAgent：模板方法 + 策略注入。
"""
from __future__ import annotations

from abc import ABC
from typing import Any, List, Optional

from ..config.role import AgentRoleConfig
from ..execution.loop_executor import ExecutionResult, ExecutorProtocol, to_agent_response
from ..models.response import AgentResponse
from ..models.session import AgentSession
from ..planning.planner import PlannerProtocol
from .tool_set import ToolSet


class BaseAgent(ABC):
    """基于模板方法的可配置 Agent。"""

    def __init__(
        self,
        *,
        config: AgentRoleConfig,
        planner: PlannerProtocol,
        executor: ExecutorProtocol,
        tool_set: ToolSet,
    ):
        self._config = config
        self._planner = planner
        self._executor = executor
        self._tool_set = tool_set

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def system_prompt(self) -> str:
        return self._config.system_prompt

    def run(
        self,
        user_input: str,
        *,
        context: Optional[Any] = None,
        session: Optional[AgentSession] = None,
    ) -> AgentResponse:
        active_session = session or AgentSession(system_prompt=self.system_prompt)
        active_session.append_user(user_input)
        steps = self.plan(user_input, session=active_session, context=context)
        result = self._executor.execute(
            user_input,
            tools=self._tool_set,
            session=active_session,
            context=context,
            steps=steps,
        )
        return self._build_response(result, steps)

    def plan(
        self,
        user_input: str,
        *,
        session: AgentSession,
        context: Optional[Any] = None,
    ) -> List[str]:
        return self._planner.plan(user_input, session=session, context=context)

    def _build_response(self, result: ExecutionResult, steps: List[str]) -> AgentResponse:
        return to_agent_response(result, steps)


class ConfigurableAgent(BaseAgent):
    """默认可配置 Agent 实现。"""

    pass
