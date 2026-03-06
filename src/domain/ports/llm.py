"""
LLM 端口定义：供领域层依赖，基础设施层负责实现。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol


@dataclass
class LLMToolCall:
    """单次 function call：id（tool_call_id）、name（工具名）、arguments（JSON 字符串）。"""

    id: str
    name: str
    arguments: str


@dataclass
class LLMReply:
    """LLM 单次回复：文本 content、可选的 tool_calls 列表、原始响应 raw。"""

    content: str
    tool_calls: List[LLMToolCall]
    raw: Any = None


class LLMEngineProtocol(Protocol):
    """LLM 调用协议：chat(messages, tools?, context?) -> LLMReply。"""

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]] | None = None,
        *,
        context: Any = None,
    ) -> LLMReply:
        ...

