"""
审计事件：记录关键操作（如 memory_updated、tool_execution）。

不记录完整 payload，仅记录 payload_hash 与 context 的 request_id/trace_id 等，
便于审计与合规的同时控制敏感信息泄露。
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("jarvis.audit")


def _hash_payload(data: Any) -> str:
    """对 payload 做稳定序列化后取 SHA256 前 16 位，用于审计去重与校验。"""
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def emit_audit_event(
    event_type: str,
    *,
    actor: str,
    context: Optional[Any] = None,
    payload: Optional[Dict[str, Any]] = None,
    status: str = "ok",
) -> None:
    """发送一条审计日志；若 context 有 to_log_fields() 则附带 request_id、trace_id 等。"""
    payload = payload or {}
    fields = {
        "event_type": event_type,
        "actor": actor,
        "status": status,
        "payload_hash": _hash_payload(payload),
    }
    if context and hasattr(context, "to_log_fields"):
        fields.update(context.to_log_fields())
    msg = " ".join(f"{k}={v}" for k, v in fields.items())
    logger.info("audit %s", msg)
