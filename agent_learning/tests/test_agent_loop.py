from core.agent import AgentConfig, SimpleAgent
from core.memory import ConversationMemory
from core.tools import build_default_tools
from core.trace import TraceLogger
from core.types import LLMResponse, ToolCall


class FakeLLMClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages, model=None, temperature=0.2, tools=None):  # noqa: ANN001
        self.calls += 1
        if self.calls == 1:
            return LLMResponse(
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="calculator",
                        arguments={"expression": "1+2"},
                    )
                ],
            )
        return LLMResponse(content="最终答案是 3")


def test_agent_runs_tool_then_returns_answer() -> None:
    agent = SimpleAgent(
        llm_client=FakeLLMClient(),  # type: ignore[arg-type]
        tools=build_default_tools(),
        memory=ConversationMemory(max_messages=10),
        trace=TraceLogger(),
        config=AgentConfig(max_steps=4),
    )
    answer = agent.run("帮我算 1+2")
    assert "3" in answer


class NeverStopLLMClient:
    def generate(self, messages, model=None, temperature=0.2, tools=None):  # noqa: ANN001
        return LLMResponse(
            content="",
            tool_calls=[ToolCall(id="call_x", name="echo", arguments={"text": "x"})],
        )


def test_agent_stops_at_max_steps() -> None:
    agent = SimpleAgent(
        llm_client=NeverStopLLMClient(),  # type: ignore[arg-type]
        tools=build_default_tools(),
        config=AgentConfig(max_steps=2),
    )
    answer = agent.run("无限循环测试")
    assert "max steps" in answer
