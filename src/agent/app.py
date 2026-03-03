from __future__ import annotations

from dataclasses import dataclass

from ..config import AGENT_CONFIG, DEFAULT_PROVIDER
from ..engine import AgentEngine
from ..tools import tool_executor, tool_registry
from .memory import FileMemoryStore, MemoryService
from .orchestrator import AgentOrchestrator, AgentOrchestratorConfig
from .planner import Planner


@dataclass
class AgentAppConfig:
    provider: str = DEFAULT_PROVIDER
    max_iterations: int = AGENT_CONFIG["max_iterations"]
    enable_planner: bool = AGENT_CONFIG["enable_planner"]
    memory_backend: str = AGENT_CONFIG["memory_backend"]
    memory_file_path: str = AGENT_CONFIG["memory_file_path"]


class AgentApp:
    def __init__(self, config: AgentAppConfig | None = None):
        self.config = config or AgentAppConfig()

        engine = AgentEngine(provider=self.config.provider)
        planner = Planner(enabled=self.config.enable_planner)
        orchestrator_config = AgentOrchestratorConfig(max_iterations=self.config.max_iterations)
        memory_service = None
        if self.config.memory_backend == "file":
            memory_service = MemoryService(
                store=FileMemoryStore(self.config.memory_file_path)
            )

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
        return response.content

