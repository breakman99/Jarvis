"""
ToolContext：工具执行时可选的上下文，由 Orchestrator 在调用 ToolExecutor 时传入。

设计意图：部分工具需要 session_id、user_id 等运行时信息时，不必通过全局状态获取。
协作：ToolExecutor.execute(tool_name, arguments, context=...) 将 context 传给
BaseTool.execute(args, context)；若工具函数签名包含 context 参数，FunctionTool 会自动注入。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolContext:
    """可选字段：session_id、user_id；extra 供扩展。"""
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

