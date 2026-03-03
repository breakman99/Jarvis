import datetime


def get_current_time():
    """返回当前系统时间"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_numbers(a: float, b: float):
    """计算两个数字之和"""
    return str(a + b)


# 统一管理工具的函数映射
AVAILABLE_FUNCTIONS = {
    "get_current_time": get_current_time,
    "add_numbers": add_numbers,
}


# 统一管理工具的描述 (Schema)
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间。用于回答时间、日期相关问题。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_numbers",
            "description": "加法计算器。当用户需要计算两个数字之和时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个加数"},
                    "b": {"type": "number", "description": "第二个加数"},
                },
                "required": ["a", "b"],
            },
        },
    },
]

