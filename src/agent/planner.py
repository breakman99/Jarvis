"""
Planner：为 Agent 提供「思考-规划-执行-复盘」的 prompt 片段与步骤占位。

当前实现为轻量级阶段化：通过 system prompt 引导模型按 Think/Plan/Act/Review 结构回复，
步骤列表由 plan_steps() 提供占位或后续从首轮回复中解析。未来可演进为显式状态机。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Planner:
    enabled: bool = False

    def planning_hint(self) -> str:
        """注入到 system prompt 的规划与阶段说明，引导模型分段输出。"""
        if not self.enabled:
            return ""
        return (
            "请按以下阶段工作（可在内心或回复中体现）：\n"
            "1. Think（思考）：理解问题、结合已有记忆与上下文。\n"
            "2. Plan（规划）：如任务较复杂，先列出解决步骤再执行。\n"
            "3. Act（执行）：按步骤调用工具或直接给出答案。\n"
            "4. Review（复盘）：在给出最终答案前，对中间结果做简短自检，再总结回答。\n"
            "若任务简单，可省略显式步骤列表，直接思考后回答。"
        )

    def plan_steps(self, user_input: str) -> List[str]:
        """返回用于 AgentResponse.steps 的占位步骤；后续可改为从首轮模型输出中解析。"""
        if not self.enabled:
            return []
        return [
            f"理解用户意图: {user_input}",
            "决定是否需要工具",
            "按需执行工具或直接回答",
            "自检并给出最终答案",
        ]

