"""
Agent 应用壳与装配层。

AgentApp 根据 AgentAppConfig 创建 LLMGateway、ToolRegistry/ToolExecutor、
MemoryService（可选）以及 AgentCoordinator（含 ConversationAgent 与可选的 PlanningAgent），
对外提供 chat(user_input) -> str。RequestContext 在此创建并透传至编排层。
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from ..config import AGENT_CONFIG, DEFAULT_PROVIDER, validate_settings
from ..engine import LLMGateway
from ..tools import create_tooling
from ..tools.context import RequestContext
from .coordinator import AgentCoordinator, ConversationAgent, PlanningAgent
from .memory import FileMemoryStore, MemoryService, SQLiteMemoryStore
from .orchestrator import AgentOrchestratorConfig
from .session import AgentSession

logger = logging.getLogger(__name__)


@dataclass
class AgentAppConfig:
    """Agent 应用配置：LLM 提供商、迭代上限、是否启用规划、记忆后端与路径。"""
    provider: str = DEFAULT_PROVIDER
    max_iterations: int = AGENT_CONFIG["max_iterations"]
    max_consecutive_tool_failures: int = AGENT_CONFIG["max_consecutive_tool_failures"]
    enable_session_trim: bool = AGENT_CONFIG["enable_session_trim"]
    max_session_messages: int = AGENT_CONFIG["max_session_messages"]
    enable_planning: bool = AGENT_CONFIG["enable_planning"]
    memory_backend: str = AGENT_CONFIG["memory_backend"]
    memory_file_path: str = AGENT_CONFIG["memory_file_path"]
    memory_db_path: str = AGENT_CONFIG["memory_db_path"]


class AgentApp:
    """统一装配入口：Coordinator + ConversationAgent + PlanningAgent。"""

    def __init__(self, config: AgentAppConfig | None = None):
        validate_settings()
        self.config = config or AgentAppConfig()

        engine = LLMGateway(provider=self.config.provider)
        orchestrator_config = AgentOrchestratorConfig(
            max_iterations=self.config.max_iterations,
            max_consecutive_tool_failures=self.config.max_consecutive_tool_failures,
            enable_session_trim=self.config.enable_session_trim,
            max_session_messages=self.config.max_session_messages,
        )
        tool_registry, tool_executor = create_tooling(register_builtin=True)
        memory_service = None
        if self.config.memory_backend == "file":
            memory_service = MemoryService(
                store=FileMemoryStore(self.config.memory_file_path)
            )
        elif self.config.memory_backend == "sqlite":
            memory_service = MemoryService(
                store=SQLiteMemoryStore(self.config.memory_db_path)
            )

        conv = ConversationAgent(
            engine=engine,
            tool_registry=tool_registry,
            tool_executor=tool_executor,
            config=orchestrator_config,
            memory_service=memory_service,
        )
        planning_agent = PlanningAgent(engine=engine) if self.config.enable_planning else None
        self.agent = AgentCoordinator(
            engine=engine,
            tool_registry=tool_registry,
            tool_executor=tool_executor,
            agents=[conv],
            memory_service=memory_service,
            planning_agent=planning_agent,
        )
        self._session_id = uuid.uuid4().hex
        self._session: AgentSession | None = None

    def chat(self, user_input: str) -> str:
        """处理一次用户输入：创建 RequestContext，委托 Coordinator 执行，返回最终文本。"""
        context = RequestContext.create(session_id=self._session_id)
        response = self.agent.run(user_input, context=context, session=self._session)
        self._session = self.agent.last_session or self._session
        logger.info(
            "event=chat_finished content_len=%s phase_log=%s request_id=%s trace_id=%s",
            len(response.content),
            response.metadata.get("phase_log"),
            context.request_id,
            context.trace_id,
        )
        return response.content

