"""
可观测性：指标（metrics）与审计（audit）。

- metrics：进程内计数与直方图，供 LLMGateway、ToolExecutor、Orchestrator 打点。
- emit_audit_event：记录关键操作（如 memory_updated、tool_execution），可带 RequestContext。
"""
from .audit import emit_audit_event
from .metrics import metrics

__all__ = ["metrics", "emit_audit_event"]

