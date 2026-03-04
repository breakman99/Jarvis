"""
BaseAgent 抽象与多 Agent 协作：可复用的 Agent 接口与 Coordinator 编排。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .response import AgentResponse
from .session import AgentSession


class BaseAgent(ABC):
    """
    抽象 Agent：统一入口为 run(user_input) -> AgentResponse；
    可选 plan() 供 Coordinator 在执行前获取步骤。
    """

    @property
    def name(self) -> str:
        """Agent 标识，用于日志与路由。"""
        return self.__class__.__name__

    def plan(self, user_input: str, session: AgentSession) -> List[str]:
        """可选：在真正执行前返回规划步骤；默认返回空列表。"""
        return []

    @abstractmethod
    def run(
        self,
        user_input: str,
        *,
        context: Optional[Any] = None,
        session: Optional[AgentSession] = None,
    ) -> AgentResponse:
        """执行一轮（或多轮）对话与工具调用，返回最终 AgentResponse。"""
        raise NotImplementedError
