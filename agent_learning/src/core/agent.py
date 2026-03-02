from __future__ import annotations

import json
from dataclasses import dataclass

from core.llm_client import LLMClient
from core.memory import ConversationMemory
from core.tools import ToolError, ToolRegistry
from core.trace import TraceLogger
from core.types import Message


@dataclass
class AgentConfig:
    system_prompt: str = (
        "You are a helpful assistant. Use tools when needed. "
        "When a tool is required, call it with valid JSON arguments."
    )
    model: str | None = None
    temperature: float = 0.2
    max_steps: int = 6


class SimpleAgent:
    def __init__(
        self,
        llm_client: LLMClient,
        tools: ToolRegistry | None = None,
        memory: ConversationMemory | None = None,
        trace: TraceLogger | None = None,
        config: AgentConfig | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.tools = tools or ToolRegistry()
        self.memory = memory or ConversationMemory()
        self.trace = trace or TraceLogger()
        self.config = config or AgentConfig()

    def run(self, task: str) -> str:
        self.memory.add(Message(role="user", content=task))
        final_answer = ""

        for step in range(1, self.config.max_steps + 1):
            context = self.memory.build_context(self.config.system_prompt)
            llm_response = self.llm_client.generate(
                messages=context,
                model=self.config.model,
                temperature=self.config.temperature,
                tools=self.tools.schemas() if len(self.tools) > 0 else None,
            )
            self.trace.add(
                step,
                "llm_response",
                {
                    "content": llm_response.content,
                    "finish_reason": llm_response.finish_reason,
                    "tool_calls": [
                        {"id": c.id, "name": c.name, "arguments": c.arguments}
                        for c in llm_response.tool_calls
                    ],
                },
            )

            if not llm_response.tool_calls:
                final_answer = llm_response.content.strip()
                self.memory.add(Message(role="assistant", content=final_answer))
                break

            assistant_tool_calls = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                }
                for call in llm_response.tool_calls
            ]
            self.memory.add(
                Message(role="assistant", content=llm_response.content, tool_calls=assistant_tool_calls)
            )

            for call in llm_response.tool_calls:
                try:
                    result = self.tools.run(call.name, call.arguments)
                except ToolError as exc:
                    result = f"Tool error: {exc}"

                self.trace.add(
                    step,
                    "tool_result",
                    {"tool": call.name, "arguments": call.arguments, "result": result},
                )
                self.memory.add(
                    Message(
                        role="tool",
                        name=call.name,
                        tool_call_id=call.id,
                        content=result,
                    )
                )
        else:
            final_answer = "Stopped: reached max steps without final answer."

        return final_answer
