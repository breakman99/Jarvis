from __future__ import annotations

from typing import Callable

from src.domain.tools.registry.registry import ToolRegistry
from src.domain.tools.runtime.executor import ToolExecutor
from src.domain.ports import LLMEngineProtocol
from ..config.role import AgentRoleConfig
from ..execution.loop_executor import LoopExecutor, LoopExecutorConfig
from ..planning.planner import DEFAULT_PLANNER_PROMPT, LLMPlanner, NullPlanner, PlannerProtocol
from .base_agent import ConfigurableAgent
from .orchestrator import AgentOrchestratorConfig
from .tool_set import ToolSet


class PlannerRegistry:
    def __init__(self) -> None:
        self._builders: dict[str, Callable[[AgentRoleConfig], PlannerProtocol]] = {}

    def register(self, planner_type: str, builder: Callable[[AgentRoleConfig], PlannerProtocol]) -> None:
        self._builders[planner_type] = builder

    def get(self, planner_type: str, config: AgentRoleConfig) -> PlannerProtocol:
        builder = self._builders.get(planner_type)
        if not builder:
            raise ValueError(f"未知 planner_type: {planner_type}")
        return builder(config)


class ExecutorRegistry:
    def __init__(self) -> None:
        self._builders: dict[str, Callable[[AgentRoleConfig], LoopExecutor]] = {}

    def register(self, executor_type: str, builder: Callable[[AgentRoleConfig], LoopExecutor]) -> None:
        self._builders[executor_type] = builder

    def get(self, executor_type: str, config: AgentRoleConfig) -> LoopExecutor:
        builder = self._builders.get(executor_type)
        if not builder:
            raise ValueError(f"未知 executor_type: {executor_type}")
        return builder(config)


class AgentFactory:
    """按角色配置构建可插拔 Agent 实例。"""

    def __init__(
        self,
        *,
        engine: LLMEngineProtocol,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        orchestrator_config: AgentOrchestratorConfig | None = None,
        planner_registry: PlannerRegistry | None = None,
        executor_registry: ExecutorRegistry | None = None,
    ):
        self._engine = engine
        self._tool_registry = tool_registry
        self._tool_executor = tool_executor
        self._orchestrator_config = orchestrator_config or AgentOrchestratorConfig()
        self._planner_registry = planner_registry or PlannerRegistry()
        self._executor_registry = executor_registry or ExecutorRegistry()
        self._register_defaults()

    def _register_defaults(self) -> None:
        if "null" not in self._planner_registry._builders:
            self._planner_registry.register("null", lambda cfg: NullPlanner())
        if "llm" not in self._planner_registry._builders:
            self._planner_registry.register(
                "llm",
                lambda cfg: LLMPlanner(engine=self._engine, system_prompt=DEFAULT_PLANNER_PROMPT),
            )
        if "loop" not in self._executor_registry._builders:
            self._executor_registry.register(
                "loop",
                lambda cfg: LoopExecutor(
                    engine=self._engine,
                    tool_executor=self._tool_executor,
                    config=LoopExecutorConfig(
                        max_iterations=cfg.max_iterations,
                        max_consecutive_tool_failures=self._orchestrator_config.max_consecutive_tool_failures,
                        enable_session_trim=self._orchestrator_config.enable_session_trim,
                        max_session_messages=self._orchestrator_config.max_session_messages,
                    ),
                ),
            )

    def create(self, config: AgentRoleConfig) -> ConfigurableAgent:
        planner = self._planner_registry.get(config.planner_type, config)
        executor = self._executor_registry.get(config.executor_type, config)
        tool_set = ToolSet(self._tool_registry, config.tool_names)
        return ConfigurableAgent(
            config=config,
            planner=planner,
            executor=executor,
            tool_set=tool_set,
        )
