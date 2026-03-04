"""
联网查询工具：HTTP GET/POST，供 Agent 在需要时访问外部 API 或网页内容。

- 适用场景：用户要求查天气、调用开放 API、获取某 URL 内容摘要等。
- 安全约定：返回内容会做长度裁剪，避免上下文过长；未来可在此增加域名白名单等策略。
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests

from ..base import ToolResult
from ..bootstrap import tool_registry

# 单次响应最大保留字符数，超出部分截断并注明
MAX_RESPONSE_CHARS = 8000


def _truncate(text: str, max_chars: int = MAX_RESPONSE_CHARS) -> str:
    """将文本截断到指定长度，并在末尾注明已截断。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[内容已截断，共 {len(text)} 字符，仅保留前 {max_chars} 字符]"


def http_get(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
) -> str:
    """
    发起 HTTP GET 请求，返回响应正文（文本或 JSON 字符串）。
    失败时抛出异常，由 ToolExecutor 捕获并转为 ToolResult。
    """
    timeout = timeout if timeout is not None else 15.0
    resp = requests.get(url, headers=headers or {}, timeout=timeout)
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
    return _truncate(text)


def http_post_json(
    url: str,
    json_body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
) -> str:
    """
    发起 HTTP POST 请求，Content-Type 为 application/json，返回响应正文摘要。
    """
    timeout = timeout if timeout is not None else 15.0
    json_body = json_body or {}
    resp = requests.post(
        url,
        json=json_body,
        headers=headers or {},
        timeout=timeout,
    )
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
    return _truncate(text)


# 注册到全局 ToolRegistry，供 Agent 使用

if not tool_registry.has("http_get"):
    tool_registry.register_function(
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
        func=http_get,
    )

if not tool_registry.has("http_post_json"):
    tool_registry.register_function(
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
        func=http_post_json,
    )
