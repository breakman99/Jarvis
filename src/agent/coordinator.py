"""
AgentCoordinator：多 Agent 编排；ConversationAgent / PlanningAgent 实现。
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from ..engine import LLMEngineProtocol
from ..tools import ToolContext, ToolExecutor, ToolRegistry
from .base_agent import BaseAgent
from .memory import MemoryService
from .orchestrator import AgentOrchestrator, AgentOrchestratorConfig
from .response import AgentResponse
from .session import AgentSession

logger = logging.getLogger(__name__)


class ConversationAgent(BaseAgent):
    """通用对话与工具执行 Agent，内部委托 AgentOrchestrator。"""

    def __init__(
        self,
        engine: LLMEngineProtocol,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        config: Optional[AgentOrchestratorConfig] = None,
        memory_service: Optional[MemoryService] = None,
    ):
        self._orchestrator = AgentOrchestrator(
            engine=engine,
            tool_registry=tool_registry,
            tool_executor=tool_executor,
            config=config or AgentOrchestratorConfig(),
            memory_service=memory_service,
        )

    def plan(self, user_input: str, session: AgentSession) -> List[str]:
        _ = user_input, session
        return []

    def run(
        self,
        user_input: str,
        *,
        context: Optional[ToolContext] = None,
        session: Optional[AgentSession] = None,
    ) -> AgentResponse:
        return self._orchestrator.run(user_input, context=context, session=session)


class PlanningAgent(BaseAgent):
    """仅做规划：调用 LLM 生成步骤列表，不执行工具。"""

    def __init__(
        self,
        engine: LLMEngineProtocol,
        system_prompt: str = "你是一个任务规划助手。根据用户输入，输出简洁的步骤列表，每行一步。不要执行工具，只输出规划。",
    ):
        self._engine = engine
        self._system_prompt = system_prompt

    def plan(
        self,
        user_input: str,
        session: AgentSession,
        *,
        context: Optional[ToolContext] = None,
    ) -> List[str]:
        history_lines: List[str] = []
        for msg in session.messages:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", "") or "").strip()
            if not content:
                continue
            history_lines.append(f"[{role}] {content}")
        history_text = "\n".join(history_lines) if history_lines else "(空)"
        messages = [
            {"role": "system", "content": self._system_prompt},
            {
                "role": "user",
                "content": (
                    "以下是当前对话的完整历史，请基于历史与新输入进行规划。\n\n"
                    f"对话历史:\n{history_text}\n\n"
                    f"本轮新输入:\n{user_input}\n\n"
                    "请输出简洁步骤，每行一步。"
                ),
            },
        ]
        try:
            response = self._engine.chat(messages, tools=None, context=context)
            content = (response.content or "").strip()
            steps = [s.strip() for s in content.split("\n") if s.strip()]
            return steps[:20]
        except Exception as e:
            logger.warning("planning_agent_plan_failed error=%s", e)
            return []

    def run(
        self,
        user_input: str,
        *,
        context: Optional[Any] = None,
        session: Optional[AgentSession] = None,
    ) -> AgentResponse:
        steps = self.plan(user_input, session or AgentSession(system_prompt=self._system_prompt))
        return AgentResponse(
            content="(规划完成)",
            steps=steps,
            metadata={"agent": self.name},
        )


class AgentCoordinator:
    """
    多 Agent 编排：持有 session、memory、engine、tools 与多个 BaseAgent；
    run() 先更新记忆，可选调用 PlanningAgent 得到步骤，再交给 ConversationAgent 执行并返回。
    """

    def __init__(
        self,
        *,
        engine: LLMEngineProtocol,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        agents: List[BaseAgent],
        memory_service: Optional[MemoryService] = None,
        system_prompt: str = "你是一个严谨的助手。请善用工具回答问题。",
        planning_agent: Optional[PlanningAgent] = None,
    ):
        self.engine = engine
        self.tool_registry = tool_registry
        self.tool_executor = tool_executor
        self._agents = {a.name: a for a in agents}
        self.memory_service = memory_service
        self._system_prompt = system_prompt
        self._planning_agent = planning_agent
        self._last_session: Optional[AgentSession] = None

    @property
    def last_session(self) -> Optional[AgentSession]:
        return self._last_session

    def run(
        self,
        user_input: str,
        *,
        context: Optional[ToolContext] = None,
        session: Optional[AgentSession] = None,
    ) -> AgentResponse:
        """
        编排一次用户请求：更新记忆、构建带记忆的 session、可选调用 PlanningAgent.plan、
        再委托 ConversationAgent.run 执行对话与工具调用，最后合并 steps 到响应。
        """
        active_context = context or ToolContext.create()
        if self.memory_service:
            self.memory_service.observe_user_input(user_input)
        prompt = self._system_prompt
        if self.memory_service:
            hint = self.memory_service.build_system_context()
            if hint:
                prompt = f"{prompt}\n\n已知用户记忆: {hint}"
        active_session = session if session is not None else AgentSession(system_prompt=prompt)

        steps: List[str] = []
        if self._planning_agent:
            steps = self._planning_agent.plan(user_input, active_session, context=active_context)
            logger.info(
                "event=coordinator_planning_steps count=%s request_id=%s trace_id=%s",
                len(steps),
                active_context.request_id,
                active_context.trace_id,
            )

        conversation = self._agents.get("ConversationAgent")
        if not conversation:
            for a in self._agents.values():
                if isinstance(a, ConversationAgent):
                    conversation = a
                    break
        if not conversation:
            raise ValueError("AgentCoordinator 需要至少一个 ConversationAgent")

        active_context.extra["memory_observed"] = True
        response = conversation.run(user_input, context=active_context, session=active_session)
        self._last_session = active_session
        if steps and not response.steps:
            response = AgentResponse(
                content=response.content,
                steps=steps,
                metadata=dict(response.metadata or {}),
            )
        return response
