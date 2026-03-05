from __future__ import annotations

from typing import Any

from ...spec.base import BaseTool, ToolResult, ToolSpec
from .common import ensure_requests, normalize_response_text


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

    def execute(self, args: dict[str, Any], context: Any | None = None) -> ToolResult:
        _ = context
        requests = ensure_requests()
        if requests is None:
            return ToolResult(ok=False, content="", error="未安装 requests，无法使用 http_post_json")
        url = args.get("url") or ""
        json_body = args.get("json_body") or {}
        headers = args.get("headers") or {}
        timeout = args.get("timeout")
        timeout = float(timeout) if timeout is not None else 15.0
        try:
            response = requests.post(url, json=json_body, headers=headers, timeout=timeout)
            response.raise_for_status()
            return ToolResult(ok=True, content=normalize_response_text(response))
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc))
