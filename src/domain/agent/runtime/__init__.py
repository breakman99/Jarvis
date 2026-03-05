"""Agent 运行时编排组件。"""

__all__ = [
    "BaseAgent",
    "ConfigurableAgent",
    "AgentCoordinator",
    "AgentRouter",
    "DefaultRouter",
    "ToolSet",
    "AgentFactory",
    "PlannerRegistry",
    "ExecutorRegistry",
    "AgentOrchestrator",
    "AgentOrchestratorConfig",
    "DEFAULT_SYSTEM_PROMPT",
]


def __getattr__(name: str):
    if name in {"BaseAgent", "ConfigurableAgent"}:
        from .base_agent import BaseAgent, ConfigurableAgent

        return {"BaseAgent": BaseAgent, "ConfigurableAgent": ConfigurableAgent}[name]
    if name in {"AgentCoordinator"}:
        from .coordinator import AgentCoordinator

        return AgentCoordinator
    if name in {"AgentFactory", "PlannerRegistry", "ExecutorRegistry"}:
        from .factory import AgentFactory, ExecutorRegistry, PlannerRegistry

        return {
            "AgentFactory": AgentFactory,
            "PlannerRegistry": PlannerRegistry,
            "ExecutorRegistry": ExecutorRegistry,
        }[name]
    if name in {"AgentRouter", "DefaultRouter"}:
        from .router import AgentRouter, DefaultRouter

        return {"AgentRouter": AgentRouter, "DefaultRouter": DefaultRouter}[name]
    if name in {"ToolSet"}:
        from .tool_set import ToolSet

        return ToolSet
    if name in {"AgentOrchestrator", "AgentOrchestratorConfig", "DEFAULT_SYSTEM_PROMPT"}:
        from .orchestrator import AgentOrchestrator, AgentOrchestratorConfig, DEFAULT_SYSTEM_PROMPT

        return {
            "AgentOrchestrator": AgentOrchestrator,
            "AgentOrchestratorConfig": AgentOrchestratorConfig,
            "DEFAULT_SYSTEM_PROMPT": DEFAULT_SYSTEM_PROMPT,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
