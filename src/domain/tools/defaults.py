"""
框架默认工具：以 BaseTool 子类实现，由 create_tooling(register_defaults=True) 或 register_default_tools(registry) 注册。

分层：本模块仅提供“开箱即用”的默认实现；业务工具应在业务侧继承 BaseTool 或使用 register_function 注册。
"""
from __future__ import annotations

import datetime
import json
from typing import Any, Dict, Optional

from .base import BaseTool, ToolResult, ToolSpec

# 单次 HTTP 响应最大保留字符数
MAX_RESPONSE_CHARS = 8000


def _truncate(text: str, max_chars: int = MAX_RESPONSE_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[内容已截断，共 {len(text)} 字符，仅保留前 {max_chars} 字符]"


# ---------------------------------------------------------------------------
# 基础工具（时间、算术）
# ---------------------------------------------------------------------------


class GetCurrentTimeTool(BaseTool):
    """获取当前本地时间。"""

    def __init__(self) -> None:
        super().__init__(
            ToolSpec(
                name="get_current_time",
                description="获取当前时间。用于回答时间、日期相关问题。",
                parameters={"type": "object", "properties": {}},
                idempotent=True,
            )
        )

    def execute(self, args: Dict[str, Any], context: Optional[Any] = None) -> ToolResult:
        _ = args, context
        s = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return ToolResult(ok=True, content=s)


class AddNumbersTool(BaseTool):
    """两数相加。"""

    def __init__(self) -> None:
        super().__init__(
            ToolSpec(
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
            )
        )

    def execute(self, args: Dict[str, Any], context: Optional[Any] = None) -> ToolResult:
        _ = context
        a = args.get("a", 0)
        b = args.get("b", 0)
        try:
            return ToolResult(ok=True, content=str(float(a) + float(b)))
        except (TypeError, ValueError) as e:
            return ToolResult(ok=False, content="", error=str(e))


# ---------------------------------------------------------------------------
# HTTP 工具
# ---------------------------------------------------------------------------

try:
    import requests
except ImportError:
    requests = None  # type: ignore


class HttpGetTool(BaseTool):
    """HTTP GET 请求，返回响应正文（截断）。"""

    def __init__(self) -> None:
        super().__init__(
            ToolSpec(
                name="http_get",
                description=(
                    "发起 HTTP GET 请求，获取指定 URL 的页面或 API 返回内容。"
                    "适用于：查询开放 API、获取网页内容摘要、查天气/新闻等。"
                    "参数 url 必须是完整的 HTTP/HTTPS 地址。"
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "完整的请求 URL，例如 https://api.example.com/data"},
                        "headers": {
                            "type": "object",
                            "description": "可选的 HTTP 请求头，键值均为字符串",
                            "additionalProperties": {"type": "string"},
                        },
                        "timeout": {"type": "number", "description": "请求超时秒数，可选，默认 15"},
                    },
                    "required": ["url"],
                },
                idempotent=True,
            )
        )

    def execute(self, args: Dict[str, Any], context: Optional[Any] = None) -> ToolResult:
        _ = context
        if requests is None:
            return ToolResult(ok=False, content="", error="未安装 requests，无法使用 http_get")
        url = args.get("url") or ""
        headers = args.get("headers") or {}
        timeout = args.get("timeout")
        timeout = float(timeout) if timeout is not None else 15.0
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if "json" in content_type:
                try:
                    data = resp.json()
                    text = json.dumps(data, ensure_ascii=False, indent=0)
                except Exception:
                    text = resp.text
            else:
                text = resp.text
            return ToolResult(ok=True, content=_truncate(text))
        except Exception as e:
            return ToolResult(ok=False, content="", error=str(e))


class HttpPostJsonTool(BaseTool):
    """HTTP POST 请求，请求体为 JSON。"""

    def __init__(self) -> None:
        super().__init__(
            ToolSpec(
                name="http_post_json",
                description=(
                    "发起 HTTP POST 请求，请求体为 JSON。"
                    "适用于：调用需要 POST 的 REST API、提交表单数据等。"
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "完整的请求 URL"},
                        "json_body": {
                            "type": "object",
                            "description": "POST 的 JSON 请求体，键值随意",
                        },
                        "headers": {
                            "type": "object",
                            "description": "可选的 HTTP 请求头",
                            "additionalProperties": {"type": "string"},
                        },
                        "timeout": {"type": "number", "description": "请求超时秒数，可选"},
                    },
                    "required": ["url"],
                },
                idempotent=False,
            )
        )

    def execute(self, args: Dict[str, Any], context: Optional[Any] = None) -> ToolResult:
        _ = context
        if requests is None:
            return ToolResult(ok=False, content="", error="未安装 requests，无法使用 http_post_json")
        url = args.get("url") or ""
        json_body = args.get("json_body") or {}
        headers = args.get("headers") or {}
        timeout = args.get("timeout")
        timeout = float(timeout) if timeout is not None else 15.0
        try:
            resp = requests.post(url, json=json_body, headers=headers, timeout=timeout)
            resp.raise_for_status()
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if "json" in content_type:
                try:
                    data = resp.json()
                    text = json.dumps(data, ensure_ascii=False, indent=0)
                except Exception:
                    text = resp.text
            else:
                text = resp.text
            return ToolResult(ok=True, content=_truncate(text))
        except Exception as e:
            return ToolResult(ok=False, content="", error=str(e))


def register_default_tools(registry) -> None:
    """将框架默认工具（时间、加法、HTTP GET/POST）注册到给定 registry；重复调用会因重名而抛错，由调用方保证只注册一次。"""
    for cls in (GetCurrentTimeTool, AddNumbersTool, HttpGetTool, HttpPostJsonTool):
        instance = cls()
        if not registry.has(instance.name):
            registry.register(instance)
