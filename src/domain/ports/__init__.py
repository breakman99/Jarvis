"""领域端口定义（由基础设施层实现）。"""

from .llm import LLMEngineProtocol, LLMReply, LLMToolCall

__all__ = ["LLMEngineProtocol", "LLMReply", "LLMToolCall"]

