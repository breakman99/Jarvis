import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.agent.orchestrator import AgentOrchestrator, AgentOrchestratorConfig  # noqa: E402
from src.domain.agent.planner import LLMPlanner  # noqa: E402
from src.domain.agent.session import AgentSession  # noqa: E402
from src.infrastructure.llm import LLMReply, LLMToolCall  # noqa: E402
from src.domain.tools.context import RequestContext  # noqa: E402
from src.domain.tools.executor import ToolExecutor  # noqa: E402
from src.domain.tools.registry import ToolRegistry  # noqa: E402


class _FailOnceTool:
    def __init__(self) -> None:
        self.calls = 0
        self.spec = type("Spec", (), {"name": "fail_once", "idempotent": True})()

    @property
    def name(self) -> str:
        return self.spec.name

    def execute(self, args, context=None):  # noqa: ANN001, ANN201
        _ = args, context
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("connection reset by peer")
        from src.domain.tools.base import ToolResult

        return ToolResult(ok=True, content="ok")


class _FailOnceNonIdempotent(_FailOnceTool):
    def __init__(self) -> None:
        super().__init__()
        self.spec = type("Spec", (), {"name": "fail_once_non_idem", "idempotent": False})()


def test_tool_executor_invalid_tool_args_should_not_crash():
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    bad_call = LLMToolCall(id="1", name="any", arguments="{bad-json")
    result = executor.execute_tool_call(bad_call, context=RequestContext.create())
    assert result.result.ok is False
    assert "参数解析失败" in (result.result.error or "")


def test_tool_executor_retry_only_for_idempotent_tool():
    registry = ToolRegistry()
    idem_tool = _FailOnceTool()
    non_idem_tool = _FailOnceNonIdempotent()
    registry.register(idem_tool)
    registry.register(non_idem_tool)
    executor = ToolExecutor(registry)

    idem_exec = executor.execute(idem_tool.name, {}, context=RequestContext.create())
    non_idem_exec = executor.execute(non_idem_tool.name, {}, context=RequestContext.create())

    assert idem_exec.result.ok is True
    assert idem_tool.calls == 2
    assert non_idem_exec.result.ok is False
    assert non_idem_tool.calls == 1


class _FakeEngine:
    def chat(self, messages, tools=None, context=None):  # noqa: ANN001, ANN201
        _ = messages, tools, context
        return LLMReply(content="done", tool_calls=[])


def test_orchestrator_returns_trace_fields_in_metadata():
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    orchestrator = AgentOrchestrator(
        engine=_FakeEngine(),
        tool_registry=registry,
        tool_executor=executor,
        config=AgentOrchestratorConfig(max_iterations=2),
    )

    response = orchestrator.run("hello", context=RequestContext.create())
    assert response.content == "done"
    assert response.metadata.get("request_id")
    assert response.metadata.get("trace_id")


class _AlwaysToolCallEngine:
    def chat(self, messages, tools=None, context=None):  # noqa: ANN001, ANN201
        _ = messages, tools, context
        if not tools:
            return LLMReply(content="finalized after failures", tool_calls=[])
        return LLMReply(
            content="",
            tool_calls=[LLMToolCall(id="c1", name="fail_once_non_idem", arguments="{}")],
        )


def test_orchestrator_should_stop_on_consecutive_tool_failures():
    registry = ToolRegistry()
    def always_fail() -> str:
        raise RuntimeError("forced failure")

    registry.register_function(
        name="fail_once_non_idem",
        description="always fail",
        parameters={"type": "object", "properties": {}},
        idempotent=False,
        func=always_fail,
    )
    executor = ToolExecutor(registry)
    orchestrator = AgentOrchestrator(
        engine=_AlwaysToolCallEngine(),
        tool_registry=registry,
        tool_executor=executor,
        config=AgentOrchestratorConfig(
            max_iterations=10,
            max_consecutive_tool_failures=2,
        ),
    )

    response = orchestrator.run("hello", context=RequestContext.create())
    assert response.metadata.get("reason") == "consecutive_tool_failures_finalized"
    assert response.content == "finalized after failures"


class _CaptureMessagesEngine:
    def __init__(self) -> None:
        self.last_messages = []

    def chat(self, messages, tools=None, context=None):  # noqa: ANN001, ANN201
        _ = tools, context
        self.last_messages = messages
        return LLMReply(content="step1\nstep2", tool_calls=[])


def test_planning_agent_should_include_full_history():
    engine = _CaptureMessagesEngine()
    planner = LLMPlanner(engine=engine)
    session = AgentSession(system_prompt="你是助手")
    session.append_user("第一个问题")
    session.append_assistant("第一个回答")
    steps = planner.plan("继续第二个问题", session=session, context=RequestContext.create())

    assert steps == ["step1", "step2"]
    assert len(engine.last_messages) == 2
    user_prompt = engine.last_messages[1]["content"]
    assert "第一个问题" in user_prompt
    assert "第一个回答" in user_prompt
    assert "继续第二个问题" in user_prompt

