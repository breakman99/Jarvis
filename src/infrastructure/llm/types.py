"""
LLM 引擎类型定义：供 Gateway 与编排层统一使用。

- LLMToolCall / LLMReply：LLM 返回的 DTO，与 OpenAI function calling 格式兼容。
- LLMEngineProtocol：LLM 调用接口协议，便于测试时注入 mock。
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
    """LLM 调用协议：chat(messages, tools?, context?) -> LLMReply，供 LLMGateway 实现、编排层依赖。"""
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]] | None = None,
        *,
        context: Any = None,
    ) -> LLMReply:
        ...
