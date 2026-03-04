import logging
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ..config import MODEL_CONFIG

logger = logging.getLogger(__name__)


class LLMGateway:
    """
    Agent 使用的唯一 LLM 网关，屏蔽不同 provider（deepseek / gemini 等）的差异。

    设计意图：Orchestrator 只依赖本网关的 chat(messages, tools) 接口，不关心
    base_url、api_key、model 名等；更换或扩展 provider 仅需改配置或本模块实现。
    协作：由 AgentApp 构造并注入 Orchestrator，日志在每次 chat 时打点（provider、latency、是否带 tools）。
    """

    def __init__(self, provider: str = "deepseek"):
        self._provider = provider
        target = MODEL_CONFIG[provider]
        self.client = OpenAI(api_key=target["api_key"], base_url=target["base_url"])
        self.model = target["model"]

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """LLM 调用统一入口，隔离 provider 差异。"""
        provider = getattr(self, "_provider", "unknown")
        used_tools = bool(tools)
        start = time.perf_counter()
        try:
            out = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "llm_chat provider=%s model=%s latency_ms=%.0f tools=%s",
                provider,
                self.model,
                latency_ms,
                used_tools,
            )
            return out
        except Exception as exc:
            logger.error(
                "llm_chat_error provider=%s model=%s error=%s",
                provider,
                self.model,
                str(exc),
            )
            raise

