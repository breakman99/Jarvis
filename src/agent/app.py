from __future__ import annotations

import logging
from dataclasses import dataclass

from ..config import AGENT_CONFIG, DEFAULT_PROVIDER
from ..engine import LLMGateway
from ..tools import tool_executor, tool_registry
from .memory import FileMemoryStore, MemoryService
from .orchestrator import AgentOrchestrator, AgentOrchestratorConfig
from .planner import Planner

logger = logging.getLogger(__name__)


"""
AgentApp：应用壳与依赖装配，对外唯一入口为 chat(user_input)。

设计意图：将「运行形态」（CLI / Web）与「Agent 内部流程」解耦；入口只持有一个
AgentApp 实例即可完成对话。协作：负责构造 LLMGateway、Planner、MemoryService、
AgentOrchestrator，并将配置（max_iterations、planner 开关、记忆后端）注入其中。
"""


@dataclass
class AgentAppConfig:
    provider: str = DEFAULT_PROVIDER
    max_iterations: int = AGENT_CONFIG["max_iterations"]
    enable_planner: bool = AGENT_CONFIG["enable_planner"]
    memory_backend: str = AGENT_CONFIG["memory_backend"]
    memory_file_path: str = AGENT_CONFIG["memory_file_path"]


class AgentApp:
    """装配 LLMGateway / Planner / Memory / Orchestrator，对外提供 chat(user_input) -> str。"""

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

