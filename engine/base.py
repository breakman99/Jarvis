from openai import OpenAI

from config import MODEL_CONFIG


class AgentEngine:
    def __init__(self, provider: str = "deepseek"):
        target = MODEL_CONFIG[provider]
        self.client = OpenAI(api_key=target["api_key"], base_url=target["base_url"])
        self.model = target["model"]

    def chat(self, messages, tools=None):
        """通用调用封装"""
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None,
        )

