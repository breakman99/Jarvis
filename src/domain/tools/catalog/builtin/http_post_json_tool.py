from __future__ import annotations

from typing import Any

from ...spec.base import BaseTool, ToolResult, ToolSpec
from .common import (
    describe_blocked_redirect,
    ensure_requests,
    normalize_response_text,
    resolve_timeout,
    validate_http_url_safety,
)


class HttpPostJsonTool(BaseTool):
    """HTTP POST 请求，请求体为 JSON。"""

    def __init__(self, *, allow_hosts: Any = None, deny_hosts: Any = None) -> None:
        self._allow_hosts = allow_hosts
        self._deny_hosts = deny_hosts
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
        requests = ensure_requests()
        if requests is None:
            return ToolResult(ok=False, content="", error="未安装 requests，无法使用 http_post_json")
        url = args.get("url") or ""
        url_error = validate_http_url_safety(
            url,
            allow_hosts=self._allow_hosts,
            deny_hosts=self._deny_hosts,
        )
        if url_error:
            return ToolResult(ok=False, content="", error=url_error)
        json_body = args.get("json_body") or {}
        headers = args.get("headers") or {}
        timeout = resolve_timeout(args.get("timeout"), context, default_timeout=15.0)
        try:
            response = requests.post(
                url,
                json=json_body,
                headers=headers,
                timeout=timeout,
                allow_redirects=False,
            )
            redirect_error = describe_blocked_redirect(
                response,
                url,
                allow_hosts=self._allow_hosts,
                deny_hosts=self._deny_hosts,
            )
            if redirect_error:
                return ToolResult(ok=False, content="", error=redirect_error)
            response.raise_for_status()
            return ToolResult(ok=True, content=normalize_response_text(response))
        except Exception as exc:
            return ToolResult(ok=False, content="", error=str(exc))
