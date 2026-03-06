from __future__ import annotations

import json
import logging
from typing import Any, List, Protocol

from src.domain.common.request_context import ToolContext
from src.domain.ports import LLMEngineProtocol
from ..models.session import AgentSession

logger = logging.getLogger(__name__)

DEFAULT_PLANNER_PROMPT = (
    "你是一个任务规划助手。根据用户输入，输出简洁的步骤列表，每行一步。"
    "不要执行工具，只输出规划。"
)


def _parse_steps(content: str) -> List[str]:
    text = (content or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            steps = [str(item).strip() for item in parsed if str(item).strip()]
            return steps[:20]
    except Exception:  # noqa: BLE001
        pass
    steps = [line.strip() for line in text.split("\n") if line.strip()]
    return steps[:20]


class PlannerProtocol(Protocol):
    def plan(
        self,
        user_input: str,
        *,
        session: AgentSession | None = None,
        context: ToolContext | None = None,
    ) -> List[str]:
        ...


class NullPlanner:
    """空规划器：直接返回空步骤。"""

    def plan(
        self,
        user_input: str,
        *,
        session: AgentSession | None = None,
        context: ToolContext | None = None,
    ) -> List[str]:
        _ = user_input, session, context
        return []


class LLMPlanner:
    """基于 LLM 的步骤规划器。"""

    def __init__(self, engine: LLMEngineProtocol, system_prompt: str = DEFAULT_PLANNER_PROMPT):
        self._engine = engine
        self._system_prompt = system_prompt

    def plan(
        self,
        user_input: str,
        *,
        session: AgentSession | None = None,
        context: ToolContext | None = None,
    ) -> List[str]:
        active_session = session or AgentSession(system_prompt=self._system_prompt)
        history_lines: List[str] = []
        for msg in active_session.messages:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", "") or "").strip()
            if content:
                history_lines.append(f"[{role}] {content}")
        history_text = "\n".join(history_lines) if history_lines else "(空)"
        messages: List[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt},
            {
                "role": "user",
                "content": (
                    "以下是当前对话的完整历史，请基于历史与新输入进行规划。\n\n"
                    f"对话历史:\n{history_text}\n\n"
                    f"本轮新输入:\n{user_input}\n\n"
                    "优先输出 JSON 数组格式步骤，例如：[\"步骤1\",\"步骤2\"]；"
                    "若无法输出 JSON，再按每行一步输出。"
                ),
            },
        ]
        try:
            response = self._engine.chat(messages, tools=None, context=context)
            return _parse_steps(response.content or "")
        except Exception as exc:  # noqa: BLE001
            logger.warning("llm_planner_plan_failed error=%s", exc)
            return []
