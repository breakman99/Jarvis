from __future__ import annotations

from typing import Any, Protocol


class AgentRouter(Protocol):
    """根据请求与上下文选择目标 Agent。"""

    def route(self, user_input: str, context: Any | None = None) -> str:
        ...


class DefaultRouter:
    """始终路由到默认 Agent。"""

    def __init__(self, default_agent_name: str):
        self._default_agent_name = default_agent_name

    def route(self, user_input: str, context: Any | None = None) -> str:
        _ = user_input, context
        return self._default_agent_name
