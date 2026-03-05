from __future__ import annotations

import json
from typing import Any

try:
    import requests
except ImportError:
    requests = None  # type: ignore

# 单次 HTTP 响应最大保留字符数
MAX_RESPONSE_CHARS = 8000


def ensure_requests() -> Any:
    return requests


def normalize_response_text(response: Any) -> str:
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "json" in content_type:
        try:
            data = response.json()
            text = json.dumps(data, ensure_ascii=False, indent=0)
        except Exception:
            text = response.text
    else:
        text = response.text
    return truncate_text(text)


def truncate_text(text: str, max_chars: int = MAX_RESPONSE_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[内容已截断，共 {len(text)} 字符，仅保留前 {max_chars} 字符]"
