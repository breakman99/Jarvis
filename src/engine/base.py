from openai import OpenAI
from typing import Any, Dict, List, Optional

from ..config import MODEL_CONFIG


class LLMGateway:
    def __init__(self, provider: str = "deepseek"):
        target = MODEL_CONFIG[provider]
        self.client = OpenAI(api_key=target["api_key"], base_url=target["base_url"])
        self.model = target["model"]

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """LLM 调用统一入口，隔离 provider 差异。"""
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None,
        )


class AgentEngine(LLMGateway):
    """向后兼容旧命名。"""

