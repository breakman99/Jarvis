from __future__ import annotations

import json
import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None  # type: ignore

# 单次 HTTP 响应最大保留字符数
MAX_RESPONSE_CHARS = 8000


def ensure_requests() -> Any:
    return requests


def _is_non_public_ip(ip_text: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _normalize_host_rules(rules: Any) -> list[str]:
    if rules is None:
        return []
    if isinstance(rules, str):
        return [item.strip().lower() for item in rules.split(",") if item.strip()]
    if isinstance(rules, (tuple, list, set)):
        return [str(item).strip().lower() for item in rules if str(item).strip()]
    return []


def _host_matches_rule(host: str, rule: str) -> bool:
    normalized_rule = rule.strip().lower()
    if not normalized_rule:
        return False
    if normalized_rule.startswith("*."):
        suffix = normalized_rule[1:]
        return host.endswith(suffix) and host != suffix[1:]
    if normalized_rule.startswith("."):
        return host.endswith(normalized_rule)
    return host == normalized_rule


def validate_http_url_safety(
    url: str,
    *,
    allow_hosts: Any = None,
    deny_hosts: Any = None,
) -> str | None:
    """
    基础 SSRF 防护：仅允许 http/https，阻止 localhost/内网/链路本地等地址。
    返回 None 表示通过；否则返回错误信息。
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return "仅允许 http/https URL"
    host = parsed.hostname
    if not host:
        return "URL 缺少主机名"
    host_lower = host.lower()
    allow_rules = _normalize_host_rules(allow_hosts)
    deny_rules = _normalize_host_rules(deny_hosts)
    if allow_rules and not any(_host_matches_rule(host_lower, rule) for rule in allow_rules):
        return "目标主机不在允许名单中"
    if any(_host_matches_rule(host_lower, rule) for rule in deny_rules):
        return "目标主机命中拒绝名单"
    if host_lower == "localhost" or host_lower.endswith(".local"):
        return "禁止访问本地或内网地址"
    if _is_non_public_ip(host_lower):
        return "禁止访问本地或内网地址"

    # 防止通过公网域名解析到内网地址（DNS Rebinding / metadata endpoint）。
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        infos = []
    except Exception:
        infos = []
    for info in infos:
        addr = info[4][0]
        if _is_non_public_ip(addr):
            return "禁止访问本地或内网地址"
    return None


def resolve_timeout(
    raw_timeout: Any,
    context: Any | None,
    *,
    default_timeout: float = 15.0,
    min_timeout: float = 0.1,
) -> float:
    """解析并约束超时时间，若有 RequestContext deadline 则不超过剩余时间。"""
    timeout = default_timeout
    if raw_timeout is not None:
        timeout = float(raw_timeout)
    if context is not None and hasattr(context, "time_left_seconds"):
        left = context.time_left_seconds()
        if left is not None:
            timeout = min(timeout, left)
    return max(min_timeout, timeout)


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
