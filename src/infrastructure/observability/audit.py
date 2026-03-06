"""
兼容层：audit 已迁移到 `src.domain.common.observability`。
"""

from src.domain.common.observability import emit_audit_event

__all__ = ["emit_audit_event"]

