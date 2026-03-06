"""
领域共享可观测性：指标（metrics）与审计事件（emit_audit_event）。
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from collections import defaultdict
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("jarvis.audit")


class MetricsCollector:
    """轻量级进程内指标收集器；线程安全，支持按 labels 区分的计数与直方图。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], int] = defaultdict(int)
        self._histograms: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], list[float]] = defaultdict(list)

    def inc(self, name: str, *, labels: Dict[str, str] | None = None, value: int = 1) -> None:
        key = (name, tuple(sorted((labels or {}).items())))
        with self._lock:
            self._counters[key] += value

    def observe(self, name: str, value: float, *, labels: Dict[str, str] | None = None) -> None:
        key = (name, tuple(sorted((labels or {}).items())))
        with self._lock:
            self._histograms[key].append(value)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "counters": {f"{k[0]}|{dict(k[1])}": v for k, v in self._counters.items()},
                "histograms": {f"{k[0]}|{dict(k[1])}": list(v) for k, v in self._histograms.items()},
            }


def _hash_payload(data: Any) -> str:
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


metrics = MetricsCollector()

