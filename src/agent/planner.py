from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Planner:
    enabled: bool = False

    def planning_hint(self) -> str:
        if not self.enabled:
            return ""
        return (
            "在调用工具前先快速思考任务步骤；如果任务简单，直接回答即可。"
            "如果任务复杂，先拆分步骤再逐步执行。"
        )

    def plan_steps(self, user_input: str) -> List[str]:
        if not self.enabled:
            return []
        return [f"理解用户意图: {user_input}", "决定是否需要工具", "生成最终答案"]

