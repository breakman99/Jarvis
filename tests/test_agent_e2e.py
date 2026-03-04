import json
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import app as agent_app_module  # noqa: E402
from src.agent.app import AgentAppConfig  # noqa: E402
from src.tools import tool_registry  # noqa: E402


class _FakeToolCallFunction:
    def __init__(self, name: str, arguments: dict) -> None:
        self.name = name
        # ToolExecutor.execute_tool_call 会把 arguments 当作 JSON 字符串解析
        self.arguments = json.dumps(arguments, ensure_ascii=False)


class _FakeToolCall:
    def __init__(self, name: str, arguments: dict, call_id: str = "call_1") -> None:
        self.id = call_id
        self.function = _FakeToolCallFunction(name, arguments)


class _FakeMessage:
    def __init__(self, content: str | None, tool_calls: list[_FakeToolCall] | None) -> None:
        self.content = content
        self.tool_calls = tool_calls


class _FakeChoice:
    def __init__(self, message: _FakeMessage) -> None:
        self.message = message


class _FakeResponse:
    def __init__(self, message: _FakeMessage) -> None:
        self.choices = [_FakeChoice(message)]


class FakeLLMNoTool:
    """始终直接给出文本答案，不触发工具调用。"""

    def __init__(self, provider: str = "deepseek") -> None:  # noqa: ARG002
        pass

    def chat(self, messages, tools=None):  # noqa: ANN001, ANN201
        _ = messages, tools
        return _FakeResponse(_FakeMessage(content="这是一个测试回答", tool_calls=None))


class FakeLLMWithAddNumbers:
    """第一轮请求触发 add_numbers 工具，第二轮返回最终答案。"""

    def __init__(self, provider: str = "deepseek") -> None:  # noqa: ARG002
        self._call_count = 0

    def chat(self, messages, tools=None):  # noqa: ANN001, ANN201
        _ = tools
        self._call_count += 1
        if self._call_count == 1:
            # 第一次调用：让 Orchestrator 走工具调用路径
            tool_call = _FakeToolCall(
                name="add_numbers",
                arguments={"a": 1, "b": 2},
                call_id="call_add_numbers",
            )
            return _FakeResponse(_FakeMessage(content=None, tool_calls=[tool_call]))

        # 第二次调用：不再触发工具，直接返回最终文本
        return _FakeResponse(_FakeMessage(content="3", tool_calls=None))


def test_agent_app_simple_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证 AgentApp 通过 LLM 直接给出答案的完整链路。"""

    # 使用假 LLM 覆盖 AgentApp 内部使用的 LLMGateway，避免真实网络调用
    monkeypatch.setattr(agent_app_module, "LLMGateway", FakeLLMNoTool)

    app = agent_app_module.AgentApp(AgentAppConfig())
    reply = app.chat("你好，简单测试一下。")

    assert "测试回答" in reply


def test_agent_app_with_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证 Agent 能够通过工具完成一次简单计算（1 + 2 = 3）。"""

    # 确认内置工具在注册表中存在
    assert tool_registry.has("add_numbers")

    # 覆盖 AgentApp 中的 LLMGateway 为假实现，驱动工具调用路径
    monkeypatch.setattr(agent_app_module, "LLMGateway", FakeLLMWithAddNumbers)

    app = agent_app_module.AgentApp(AgentAppConfig())
    reply = app.chat("请帮我计算 1 加 2 等于多少？")

    assert "3" in reply

