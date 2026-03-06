"""
兼容层：LLM 类型已迁移到 `src.domain.ports.llm`。
"""

from src.domain.ports.llm import LLMEngineProtocol, LLMReply, LLMToolCall

__all__ = ["LLMReply", "LLMToolCall", "LLMEngineProtocol"]
