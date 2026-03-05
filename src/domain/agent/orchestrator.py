"""
Orchestrator 兼容层：内部委托 LoopExecutor，保留旧调用入口。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.domain.tools import ToolContext, ToolExecutor, ToolRegistry
from src.infrastructure.llm import LLMEngineProtocol
from .agent_executor import LoopExecutor, LoopExecutorConfig, to_agent_response
from .response import AgentResponse
from .session import AgentSession
from .tool_set import ToolSet

DEFAULT_SYSTEM_PROMPT = "你是一个严谨的助手。请善用工具回答问题。"


@dataclass
class AgentOrchestratorConfig:
    """兼容旧配置结构；执行期参数映射到 LoopExecutorConfig。"""

    max_iterations: int = 5
    max_consecutive_tool_failures: int = 3
    enable_session_trim: bool = False
    max_session_messages: int = 80
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


class AgentOrchestrator:
    """兼容旧接口的执行器封装。"""

    def __init__(
        self,
        *,
        engine: LLMEngineProtocol,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        config: Optional[AgentOrchestratorConfig] = None,
        memory_service: object | None = None,
    ):
        _ = memory_service
        self._tool_registry = tool_registry
        self._config = config or AgentOrchestratorConfig()
        self._executor = LoopExecutor(
            engine=engine,
            tool_executor=tool_executor,
            config=LoopExecutorConfig(
                max_iterations=self._config.max_iterations,
                max_consecutive_tool_failures=self._config.max_consecutive_tool_failures,
                enable_session_trim=self._config.enable_session_trim,
                max_session_messages=self._config.max_session_messages,
            ),
        )

    def run(
        self,
        user_input: str,
        *,
        context: Optional[ToolContext] = None,
        session: Optional[AgentSession] = None,
    ) -> AgentResponse:
        active_session = session or AgentSession(system_prompt=self._config.system_prompt)
        active_session.append_user(user_input)
        result = self._executor.execute(
            user_input,
            tools=ToolSet(self._tool_registry),
            session=active_session,
            context=context,
            steps=[],
        )
        return to_agent_response(result, [])
