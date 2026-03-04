from __future__ import annotations

import logging
from dataclasses import dataclass

from ..config import AGENT_CONFIG, DEFAULT_PROVIDER
from ..engine import LLMGateway
from ..tools import tool_executor, tool_registry
from .coordinator import AgentCoordinator, ConversationAgent, PlanningAgent
from .memory import FileMemoryStore, MemoryService, SQLiteMemoryStore
from .orchestrator import AgentOrchestrator, AgentOrchestratorConfig
from .planner import Planner

logger = logging.getLogger(__name__)


@dataclass
class AgentAppConfig:
    provider: str = DEFAULT_PROVIDER
    max_iterations: int = AGENT_CONFIG["max_iterations"]
    enable_planner: bool = AGENT_CONFIG["enable_planner"]
    memory_backend: str = AGENT_CONFIG["memory_backend"]
    memory_file_path: str = AGENT_CONFIG["memory_file_path"]
    memory_db_path: str = AGENT_CONFIG["memory_db_path"]
    enable_multi_agent: bool = bool(AGENT_CONFIG.get("enable_multi_agent", False))


class AgentApp:
    """装配 LLMGateway / Planner / Memory / Orchestrator 或 AgentCoordinator，对外提供 chat(user_input) -> str。"""

    def __init__(self, config: AgentAppConfig | None = None):
        self.config = config or AgentAppConfig()

        engine = LLMGateway(provider=self.config.provider)
        planner = Planner(enabled=self.config.enable_planner)
        orchestrator_config = AgentOrchestratorConfig(max_iterations=self.config.max_iterations)
        memory_service = None
        if self.config.memory_backend == "file":
            memory_service = MemoryService(
                store=FileMemoryStore(self.config.memory_file_path)
            )
        elif self.config.memory_backend == "sqlite":
            memory_service = MemoryService(
                store=SQLiteMemoryStore(self.config.memory_db_path)
            )

        if self.config.enable_multi_agent:
            conv = ConversationAgent(
                engine=engine,
                tool_registry=tool_registry,
                tool_executor=tool_executor,
                config=orchestrator_config,
                planner=planner,
                memory_service=memory_service,
            )
            planning_agent = PlanningAgent(engine=engine) if self.config.enable_planner else None
            self.agent = AgentCoordinator(
                engine=engine,
                tool_registry=tool_registry,
                tool_executor=tool_executor,
                agents=[conv],
                memory_service=memory_service,
                planning_agent=planning_agent,
            )
        else:
            self.agent = AgentOrchestrator(
                engine=engine,
                tool_registry=tool_registry,
                tool_executor=tool_executor,
                planner=planner,
                config=orchestrator_config,
                memory_service=memory_service,
            )

    def chat(self, user_input: str) -> str:
        response = self.agent.run(user_input)
        logger.info(
            "chat finished content_len=%s phase_log=%s",
            len(response.content),
            response.metadata.get("phase_log"),
        )
        return response.content

