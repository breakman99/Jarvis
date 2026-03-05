"""
LLM 网关：唯一 LLM 调用出入口，支持可配置重试、超时与错误分类。
"""
from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.infrastructure.common import CancelledError, TimeoutError, TransientError
from src.infrastructure.config import LLM_CONFIG, get_provider_model_config, load_model_config
from src.infrastructure.observability import metrics
from src.domain.tools.runtime.context import RequestContext
from .types import LLMReply, LLMToolCall

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """判定是否为可重试错误：网络、超时、5xx、429。"""
    msg = (getattr(exc, "message", None) or str(exc)).lower()
    if "timeout" in msg or "timed out" in msg:
        return True
    if "connection" in msg or "connect" in msg:
        return True
    code = getattr(exc, "status_code", None)
    if code is not None:
        if code == 429:
            return True
        if 500 <= (code if isinstance(code, int) else 0) < 600:
            return True
    # OpenAI 异常类型
    t = type(exc).__name__
    if "RateLimit" in t or "Timeout" in t or "Connection" in t or "APIConnection" in t:
        return True
    if "APIStatusError" in t and hasattr(exc, "status_code"):
        sc = getattr(exc, "status_code", 0)
        if sc == 429 or (isinstance(sc, int) and 500 <= sc < 600):
            return True
    return False


class LLMGateway:
    """
    Agent 使用的唯一 LLM 网关，屏蔽 provider 差异；支持重试、超时与错误分类。
    """

    def __init__(self, provider: str = "deepseek"):
        model_config = load_model_config()
        if provider not in model_config:
            raise ValueError(f"未知 provider: {provider}，可选: {list(model_config.keys())}")
        self._provider = provider
        target = get_provider_model_config(provider)
        api_key = target.get("api_key") or ""
        base_url = target.get("base_url") or ""
        if not api_key:
            logger.warning(
                "llm_gateway provider=%s api_key 未设置，请配置环境变量（如 DEEPSEEK_API_KEY）",
                provider,
            )
        self.client = OpenAI(api_key=api_key or "sk-placeholder", base_url=base_url)
        self.model = target.get("model", "deepseek-chat")
        self._max_retries = LLM_CONFIG.get("max_retries", 3)
        self._base_backoff_ms = LLM_CONFIG.get("base_backoff_ms", 1000)
        self._max_backoff_ms = LLM_CONFIG.get("max_backoff_ms", 30000)
        self._timeout_seconds = LLM_CONFIG.get("timeout_seconds", 60)

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        *,
        context: Optional[RequestContext] = None,
    ) -> LLMReply:
        """LLM 调用统一入口：重试可重试错误，指数退避+抖动。"""
        provider = getattr(self, "_provider", "unknown")
        used_tools = bool(tools)
        last_exc: Optional[BaseException] = None
        for attempt in range(self._max_retries + 1):
            if context and context.should_stop():
                if context.cancelled:
                    raise CancelledError()
                raise TimeoutError("request deadline exceeded before llm call")
            start = time.perf_counter()
            try:
                timeout_seconds = float(self._timeout_seconds)
                if context:
                    left = context.time_left_seconds()
                    if left is not None:
                        timeout_seconds = max(0.1, min(timeout_seconds, left))
                out = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto" if tools else None,
                    timeout=timeout_seconds,
                )
                latency_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "event=llm_chat provider=%s model=%s latency_ms=%.0f tools=%s request_id=%s trace_id=%s",
                    provider,
                    self.model,
                    latency_ms,
                    used_tools,
                    context.request_id if context else "",
                    context.trace_id if context else "",
                )
                metrics.inc(
                    "llm_calls_total",
                    labels={"provider": provider, "model": self.model, "status": "ok"},
                )
                metrics.observe(
                    "llm_call_latency_ms",
                    latency_ms,
                    labels={"provider": provider, "model": self.model},
                )
                msg = out.choices[0].message
                tool_calls = []
                for call in msg.tool_calls or []:
                    tool_calls.append(
                        LLMToolCall(
                            id=getattr(call, "id", "") or "",
                            name=call.function.name,
                            arguments=call.function.arguments or "{}",
                        )
                    )
                return LLMReply(content=msg.content or "", tool_calls=tool_calls, raw=out)
            except Exception as exc:
                last_exc = exc
                latency_ms = (time.perf_counter() - start) * 1000.0
                logger.error(
                    "event=llm_chat_error provider=%s model=%s attempt=%s error=%s request_id=%s trace_id=%s",
                    provider,
                    self.model,
                    attempt + 1,
                    str(exc),
                    context.request_id if context else "",
                    context.trace_id if context else "",
                )
                metrics.inc(
                    "llm_calls_total",
                    labels={"provider": provider, "model": self.model, "status": "error"},
                )
                metrics.observe(
                    "llm_call_latency_ms",
                    latency_ms,
                    labels={"provider": provider, "model": self.model},
                )
                if attempt == self._max_retries or not _is_retryable(exc):
                    raise
                if context and context.should_stop():
                    if context.cancelled:
                        raise CancelledError()
                    raise TimeoutError("request deadline exceeded during llm retry")
                backoff_ms = min(
                    self._base_backoff_ms * (2 ** attempt),
                    self._max_backoff_ms,
                )
                jitter = backoff_ms * 0.2 * (random.random() * 2 - 1)
                sleep_sec = (backoff_ms + jitter) / 1000.0
                logger.info(
                    "event=llm_chat_retry provider=%s backoff_ms=%.0f next_attempt=%s request_id=%s trace_id=%s",
                    provider,
                    sleep_sec * 1000,
                    attempt + 2,
                    context.request_id if context else "",
                    context.trace_id if context else "",
                )
                metrics.inc(
                    "retry_total",
                    labels={"layer": "llm", "reason": type(exc).__name__},
                )
                time.sleep(sleep_sec)
        if last_exc is not None:
            raise TransientError(str(last_exc), error_code="LLM_RETRY_EXHAUSTED")
        raise RuntimeError("llm_chat unexpected exit")
