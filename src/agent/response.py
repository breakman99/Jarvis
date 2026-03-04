from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentResponse:
    """Agent 单次对话的返回：最终答案、规划/执行轨迹、以及可选的阶段与原因等。"""

    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    steps: List[str] = field(default_factory=list)

    # metadata 常见键（可选）：
    # - phase_log: List[str]，阶段列表，如 ['think','plan','act','review']
    # - reason: str，如 'max_iterations_reached'

