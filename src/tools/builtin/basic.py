"""
基础内置工具：当前时间、加法。

供 Agent 回答时间/日期问题与简单数值计算；均标记为 idempotent 以支持重试。
"""
import datetime


def get_current_time() -> str:
    """返回当前本地时间，格式 YYYY-MM-DD HH:MM:SS。"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_numbers(a: float, b: float) -> str:
    """两数相加，返回和的字符串形式。"""
    return str(a + b)


def register_tools(registry) -> None:
    """将 get_current_time、add_numbers 注册到 registry（若尚未注册）。"""
    if not registry.has("get_current_time"):
        registry.register_function(
            name="get_current_time",
            description="获取当前时间。用于回答时间、日期相关问题。",
            parameters={"type": "object", "properties": {}},
            idempotent=True,
            func=get_current_time,
        )
    if not registry.has("add_numbers"):
        registry.register_function(
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
            idempotent=True,
            func=add_numbers,
        )

