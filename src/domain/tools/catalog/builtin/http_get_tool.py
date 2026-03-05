from __future__ import annotations

from typing import Any

from ...spec.base import BaseTool, ToolResult, ToolSpec
from .common import ensure_requests, normalize_response_text


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

    def execute(self, args: dict[str, Any], context: Any | None = None) -> ToolResult:
        _ = context
        requests = ensure_requests()
        if requests is None:
            return ToolResult(ok=False, content="", error="未安装 requests，无法使用 http_get")
        url = args.get("url") or ""
        headers = args.get("headers") or {}
        timeout = args.get("timeout")
        timeout = float(timeout) if timeout is not None else 15.0
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return ToolResult(ok=True, content=normalize_response_text(response))
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc))
