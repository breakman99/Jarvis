from core.tools import ToolError, build_default_tools


def test_tool_registry_has_default_tools() -> None:
    registry = build_default_tools()
    assert len(registry) == 3


def test_calculator_tool_works() -> None:
    registry = build_default_tools()
    result = registry.run("calculator", {"expression": "2*(3+4)"})
    assert result == "14.0"


def test_unknown_tool_raises_error() -> None:
    registry = build_default_tools()
    try:
        registry.run("unknown_tool", {})
        assert False, "Expected ToolError"
    except ToolError:
        assert True
