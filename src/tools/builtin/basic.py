import datetime

from ..bootstrap import tool, tool_registry


@tool(
    description="获取当前时间。用于回答时间、日期相关问题。",
    parameters={"type": "object", "properties": {}},
)
def get_current_time() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_numbers(a: float, b: float) -> str:
    return str(a + b)


if not tool_registry.has("add_numbers"):
    tool_registry.register_function(
        name="add_numbers",
        description="加法计算器。当用户需要计算两个数字之和时使用。",
        parameters={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "第一个加数"},
                "b": {"type": "number", "description": "第二个加数"},
            },
            "required": ["a", "b"],
        },
        func=add_numbers,
    )

