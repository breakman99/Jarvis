from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from core.types import LLMResponse, Message, ToolCall


class LLMClient:
    def __init__(self, api_key: str, base_url: str, default_model: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required.")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.default_model = default_model

    @staticmethod
    def _to_openai_messages(messages: list[Message]) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for msg in messages:
            item: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            payload.append(item)
        return payload

    def generate(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float = 0.2,
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        request: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": self._to_openai_messages(messages),
            "temperature": temperature,
        }
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"

        completion = self.client.chat.completions.create(**request)
        first = completion.choices[0]
        message = first.message

        parsed_tool_calls: list[ToolCall] = []
        for call in message.tool_calls or []:
            raw_arguments = call.function.arguments or "{}"
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                arguments = {"raw": raw_arguments}
            parsed_tool_calls.append(
                ToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=arguments,
                )
            )

        return LLMResponse(
            content=message.content or "",
            tool_calls=parsed_tool_calls,
            finish_reason=first.finish_reason,
        )
