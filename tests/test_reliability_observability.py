import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.agent.models.session import AgentSession  # noqa: E402
from src.domain.agent.planning.planner import LLMPlanner  # noqa: E402
from src.domain.agent.runtime.orchestrator import AgentOrchestrator, AgentOrchestratorConfig  # noqa: E402
from src.domain.tools.catalog.builtin import AddNumbersTool, HttpGetTool  # noqa: E402
from src.domain.tools.catalog.builtin.common import validate_http_url_safety  # noqa: E402
from src.domain.tools.spec.base import BaseTool, ToolResult, ToolSpec  # noqa: E402
from src.infrastructure.llm import LLMReply, LLMToolCall  # noqa: E402
from src.domain.tools.registry import ToolRegistry  # noqa: E402
from src.domain.tools.runtime.context import RequestContext  # noqa: E402
from src.domain.tools.runtime.executor import ToolExecutor  # noqa: E402


class _FailOnceTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            ToolSpec(
                name="fail_once",
                description="fail once",
                parameters={"type": "object", "properties": {}},
                idempotent=True,
            )
        )
        self.calls = 0

    def execute(self, args, context=None):  # noqa: ANN001, ANN201
        _ = args, context
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("connection reset by peer")

        return ToolResult(ok=True, content="ok")


class _FailOnceNonIdempotent(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            ToolSpec(
                name="fail_once_non_idem",
                description="fail once non idempotent",
                parameters={"type": "object", "properties": {}},
                idempotent=False,
            ),
        )
        self.calls = 0

    def execute(self, args, context=None):  # noqa: ANN001, ANN201
        _ = args, context
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("connection reset by peer")
        return ToolResult(ok=True, content="ok")


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


def test_tool_executor_should_validate_schema_before_execute():
    registry = ToolRegistry()
    registry.register(AddNumbersTool())
    executor = ToolExecutor(registry)

    bad_exec = executor.execute("add_numbers", {"a": 1}, context=RequestContext.create())

    assert bad_exec.result.ok is False
    assert "参数校验失败" in (bad_exec.result.error or "")
    assert "args.b" in (bad_exec.result.error or "")


def test_http_tool_should_block_private_network_url():
    registry = ToolRegistry()
    registry.register(HttpGetTool())
    executor = ToolExecutor(registry)

    blocked_exec = executor.execute(
        "http_get",
        {"url": "http://127.0.0.1:8080/healthz"},
        context=RequestContext.create(),
    )

    assert blocked_exec.result.ok is False
    assert "禁止访问本地或内网地址" in (blocked_exec.result.error or "")


def test_http_url_safety_should_apply_allowlist_and_denylist():
    allowed = validate_http_url_safety(
        "https://api.example.com/v1",
        allow_hosts=("api.example.com",),
    )
    blocked_by_allowlist = validate_http_url_safety(
        "https://www.example.com",
        allow_hosts=("api.example.com",),
    )
    blocked_by_denylist = validate_http_url_safety(
        "https://api.example.com",
        deny_hosts=("api.example.com",),
    )

    assert allowed is None
    assert blocked_by_allowlist == "目标主机不在允许名单中"
    assert blocked_by_denylist == "目标主机命中拒绝名单"


def test_http_url_safety_should_support_wildcard_rule():
    ok = validate_http_url_safety("https://a.service.example.com", allow_hosts=("*.example.com",))
    blocked = validate_http_url_safety("https://example.com", allow_hosts=("*.example.com",))

    assert ok is None
    assert blocked == "目标主机不在允许名单中"


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


class _AlwaysFailTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            ToolSpec(
                name="fail_once_non_idem",
                description="always fail",
                parameters={"type": "object", "properties": {}},
                idempotent=False,
            )
        )

    def execute(self, args, context=None):  # noqa: ANN001, ANN201
        _ = args, context
        raise RuntimeError("forced failure")


def test_orchestrator_should_stop_on_consecutive_tool_failures():
    registry = ToolRegistry()
    registry.register(_AlwaysFailTool())
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


class _JsonPlanEngine:
    def chat(self, messages, tools=None, context=None):  # noqa: ANN001, ANN201
        _ = messages, tools, context
        return LLMReply(content='["step-a", "step-b"]', tool_calls=[])


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


def test_planning_agent_should_parse_json_steps():
    planner = LLMPlanner(engine=_JsonPlanEngine())
    steps = planner.plan("做一个简单计划", session=AgentSession(system_prompt="你是助手"))
    assert steps == ["step-a", "step-b"]
