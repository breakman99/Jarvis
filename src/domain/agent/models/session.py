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

    def refresh_system_prompt(self, system_prompt: str) -> None:
        """刷新会话中的 system prompt，确保复用 session 时记忆上下文可更新。"""
        self.system_prompt = system_prompt
        if not self.messages:
            self.messages.append({"role": "system", "content": system_prompt})
            return
        if self.messages[0].get("role") == "system":
            self.messages[0]["content"] = system_prompt
            return
        self.messages.insert(0, {"role": "system", "content": system_prompt})

    def trim(self, *, max_messages: int) -> None:
        """
        裁剪会话消息数量，保留首条 system 消息与末尾若干条消息。

        额外约束：
        - 不保留“孤立”的 tool 消息（必须有同一裁剪窗口内的 assistant.tool_calls 对应）。
        - 不保留“未闭合”的 assistant.tool_calls（其后必须包含对应 tool 回包）。
        """
        if max_messages <= 1 or len(self.messages) <= max_messages:
            return
        system = self.messages[0]
        tail = self.messages[1:]
        tail_keep = max_messages - 1
        start_min = max(0, len(tail) - tail_keep)
        selected = tail[start_min:]
        if not self._is_tool_sequence_well_formed(selected):
            for idx in range(start_min + 1, len(tail) + 1):
                candidate = tail[idx:]
                if self._is_tool_sequence_well_formed(candidate):
                    selected = candidate
                    break
            else:
                selected = []
        self.messages = [system] + selected

    @staticmethod
    def _is_tool_sequence_well_formed(messages: List[Message]) -> bool:
        """
        校验消息切片中的工具调用关系是否闭合：
        assistant(tool_calls) 必须在后续收到全部 tool 回包，且不得出现孤立 tool。
        """
        pending_tool_call_ids: set[str] = set()
        for message in messages:
            role = str(message.get("role") or "")
            if role == "assistant":
                if pending_tool_call_ids:
                    return False
                raw_calls = message.get("tool_calls") or []
                if isinstance(raw_calls, list):
                    for call in raw_calls:
                        if not isinstance(call, dict):
                            continue
                        call_id = str(call.get("id") or "")
                        if call_id:
                            pending_tool_call_ids.add(call_id)
                continue
            if role == "tool":
                tool_call_id = str(message.get("tool_call_id") or "")
                if not tool_call_id or tool_call_id not in pending_tool_call_ids:
                    return False
                pending_tool_call_ids.remove(tool_call_id)
                continue
            if pending_tool_call_ids:
                return False
        return not pending_tool_call_ids
