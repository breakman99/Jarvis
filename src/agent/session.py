"""
Agent 会话：维护单次请求内的消息列表（system / user / assistant / tool）。

与 OpenAI 对话格式兼容，供 Orchestrator 在每轮 LLM 调用前后追加 user、assistant、tool 消息。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


Message = Dict[str, Any]


@dataclass
class AgentSession:
    """单次请求的对话会话：system_prompt + messages 列表，提供 append_* 方法追加各角色消息。"""
    system_prompt: str
    messages: List[Message] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.messages:
            self.messages.append({"role": "system", "content": self.system_prompt})

    def append_user(self, content: str) -> None:
        """追加一条 user 消息。"""
        self.messages.append({"role": "user", "content": content})

    def append_assistant(self, content: Optional[str]) -> None:
        """追加一条无 tool_calls 的 assistant 消息。"""
        self.messages.append({"role": "assistant", "content": content or ""})

    def append_assistant_tool_calls(self, model_message: Any) -> None:
        """从模型返回的 message 对象中解析 tool_calls 并追加为 assistant 消息。"""
        if model_message is None:
            return
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

    def append_assistant_tool_calls_data(self, content: str, tool_calls_data: List[Dict[str, Any]]) -> None:
        """直接使用已构造的 tool_calls 列表追加为 assistant 消息。"""
        self.messages.append(
            {
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls_data,
            }
        )

    def append_tool_message(self, message: Message) -> None:
        """追加一条 role=tool 的消息（工具执行结果）。"""
        self.messages.append(message)

