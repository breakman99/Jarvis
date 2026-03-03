from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


Message = Dict[str, Any]


@dataclass
class AgentSession:
    system_prompt: str
    messages: List[Message] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.messages:
            self.messages.append({"role": "system", "content": self.system_prompt})

    def append_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def append_assistant(self, content: Optional[str]) -> None:
        self.messages.append({"role": "assistant", "content": content or ""})

    def append_assistant_tool_calls(self, model_message: Any) -> None:
        tool_calls = []
        for call in model_message.tool_calls or []:
            tool_calls.append(
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
            )
        self.messages.append(
            {
                "role": "assistant",
                "content": model_message.content or "",
                "tool_calls": tool_calls,
            }
        )

    def append_tool_message(self, message: Message) -> None:
        self.messages.append(message)

