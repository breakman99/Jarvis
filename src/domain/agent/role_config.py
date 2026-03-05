from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentRoleConfig:
    """声明式 Agent 角色配置。"""

    name: str
    system_prompt: str
    tool_names: list[str] | None = None
    planner_type: str = "null"
    executor_type: str = "loop"
    max_iterations: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)
