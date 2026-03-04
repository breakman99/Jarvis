"""
RequestContext：请求级上下文，在 App/Coordinator/Orchestrator/Engine/Tool 全链路透传。

设计意图：统一 request_id / trace_id / session_id / deadline 等横切信息，便于可靠性控制
（超时、取消）和可观测性（日志、审计、指标）。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RequestContext:
    """请求级上下文；extra 用于传递链路内控制标记。"""
    request_id: str
    trace_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    deadline_ts: Optional[float] = None
    cancelled: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> "RequestContext":
        now = time.time()
        request_id = uuid.uuid4().hex
        trace_id = uuid.uuid4().hex
        deadline_ts = None
        if timeout_seconds is not None and timeout_seconds > 0:
            deadline_ts = now + timeout_seconds
        return cls(
            request_id=request_id,
            trace_id=trace_id,
            session_id=session_id,
            user_id=user_id,
            deadline_ts=deadline_ts,
        )

    def is_expired(self) -> bool:
        return self.deadline_ts is not None and time.time() >= self.deadline_ts

    def should_stop(self) -> bool:
        return self.cancelled or self.is_expired()

    def to_log_fields(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "session_id": self.session_id or "",
            "user_id": self.user_id or "",
        }


# Backward compatibility.
ToolContext = RequestContext

