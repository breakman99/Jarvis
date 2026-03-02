from __future__ import annotations

from dataclasses import dataclass, field

from core.types import Message


@dataclass
class ConversationMemory:
    max_messages: int = 20
    _messages: list[Message] = field(default_factory=list)

    def add(self, message: Message) -> None:
        self._messages.append(message)
        self._trim()

    def extend(self, messages: list[Message]) -> None:
        self._messages.extend(messages)
        self._trim()

    def clear(self) -> None:
        self._messages.clear()

    def history(self) -> list[Message]:
        return list(self._messages)

    def build_context(self, system_prompt: str) -> list[Message]:
        return [Message(role="system", content=system_prompt), *self.history()]

    def _trim(self) -> None:
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages :]
