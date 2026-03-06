"""
兼容层：历史上 RequestContext 位于 tools.runtime.context。

当前 RequestContext 已迁移至 `src.domain.common.request_context`，
本模块仅做 re-export，避免存量导入路径中断。
"""

from src.domain.common.request_context import RequestContext, ToolContext

__all__ = ["RequestContext", "ToolContext"]

