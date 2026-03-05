import json
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.application.app as agent_app_module  # noqa: E402
from src.application.app import AgentAppConfig  # noqa: E402
from src.infrastructure.llm import LLMReply, LLMToolCall  # noqa: E402


class FakeLLMNoTool:
    """始终直接给出文本答案，不触发工具调用。"""

    def __init__(self, provider: str = "deepseek") -> None:  # noqa: ARG002
        pass

    def chat(self, messages, tools=None, context=None):  # noqa: ANN001, ANN201
        _ = messages, tools, context
        return LLMReply(content="这是一个测试回答", tool_calls=[])


class FakeLLMWithAddNumbers:
    """第一轮请求触发 add_numbers 工具，第二轮返回最终答案。"""

    def __init__(self, provider: str = "deepseek") -> None:  # noqa: ARG002
        self._call_count = 0

    def chat(self, messages, tools=None, context=None):  # noqa: ANN001, ANN201
        _ = tools, messages, context
        self._call_count += 1
        if self._call_count == 1:
            # 第一次调用：让 Orchestrator 走工具调用路径
            tool_call = LLMToolCall(
                name="add_numbers",
                arguments=json.dumps({"a": 1, "b": 2}, ensure_ascii=False),
                id="call_add_numbers",
            )
            return LLMReply(content="", tool_calls=[tool_call])

        # 第二次调用：不再触发工具，直接返回最终文本
        return LLMReply(content="3", tool_calls=[])


class FakeLLMCountUserMessages:
    """返回当前 messages 中 user 消息数量，用于验证会话历史是否保留。"""

    def __init__(self, provider: str = "deepseek") -> None:  # noqa: ARG002
        pass

    def chat(self, messages, tools=None, context=None):  # noqa: ANN001, ANN201
        _ = tools, context
        user_count = sum(1 for m in messages if m.get("role") == "user")
        return LLMReply(content=f"user_count={user_count}", tool_calls=[])


class FakeLLMCaptureSystemPrompt:
    """记录每次调用时的 system prompt。"""

    def __init__(self, provider: str = "deepseek") -> None:  # noqa: ARG002
        self.system_prompts: list[str] = []

    def chat(self, messages, tools=None, context=None):  # noqa: ANN001, ANN201
        _ = tools, context
        system_content = ""
        if messages and messages[0].get("role") == "system":
            system_content = str(messages[0].get("content", ""))
        self.system_prompts.append(system_content)
        return LLMReply(content="ok", tool_calls=[])


def test_agent_app_simple_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证 AgentApp 通过 LLM 直接给出答案的完整链路。"""

    # 使用假 LLM 覆盖 AgentApp 内部使用的 LLMGateway，避免真实网络调用
    monkeypatch.setattr(agent_app_module, "LLMGateway", FakeLLMNoTool)

    app = agent_app_module.AgentApp(AgentAppConfig())
    reply = app.chat("你好，简单测试一下。")

    assert "测试回答" in reply


def test_agent_app_with_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证 Agent 能够通过工具完成一次简单计算（1 + 2 = 3）。"""

    # 覆盖 AgentApp 中的 LLMGateway 为假实现，驱动工具调用路径
    monkeypatch.setattr(agent_app_module, "LLMGateway", FakeLLMWithAddNumbers)

    app = agent_app_module.AgentApp(AgentAppConfig())
    reply = app.chat("请帮我计算 1 加 2 等于多少？")

    assert "3" in reply


def test_agent_app_should_keep_session_history(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_app_module, "LLMGateway", FakeLLMCountUserMessages)

    app = agent_app_module.AgentApp(
        AgentAppConfig(enable_planning=False)
    )
    first = app.chat("第一句")
    second = app.chat("第二句")

    assert "user_count=1" in first
    assert "user_count=2" in second


def test_agent_app_should_refresh_memory_context_on_reused_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    fake_llm = FakeLLMCaptureSystemPrompt()
    monkeypatch.setattr(agent_app_module, "LLMGateway", lambda provider: fake_llm)

    memory_file = tmp_path / "memory.json"
    app = agent_app_module.AgentApp(
        AgentAppConfig(
            enable_planning=False,
            memory_backend="file",
            memory_file_path=str(memory_file),
        )
    )

    app.chat("你好")
    app.chat("我叫小明")

    assert len(fake_llm.system_prompts) == 2
    assert "用户名字是 小明" in fake_llm.system_prompts[1]

