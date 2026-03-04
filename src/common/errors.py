"""
Jarvis 统一错误类型：便于上层区分可重试与不可重试、超时与取消。

- TransientError：临时错误（如网络、5xx），可重试。
- PermanentError：永久错误（如 4xx、参数错误），不重试。
- TimeoutError / CancelledError：用于 deadline 与取消控制，由 RequestContext.should_stop 触发。
"""
from __future__ import annotations


class JarvisError(Exception):
    """Jarvis 基础异常，携带 error_code 便于分类与日志。"""
    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class TransientError(JarvisError):
    """临时错误：网络、超时、5xx 等，调用方可选择重试。"""
    def __init__(self, message: str, *, error_code: str = "TRANSIENT") -> None:
        super().__init__(message, error_code=error_code)


class PermanentError(JarvisError):
    """永久错误：认证、参数、4xx 等，不应重试。"""
    def __init__(self, message: str, *, error_code: str = "PERMANENT") -> None:
        super().__init__(message, error_code=error_code)


class TimeoutError(PermanentError):
    """请求或操作超时（如 deadline_ts 已过）。"""
    def __init__(self, message: str = "operation timed out") -> None:
        super().__init__(message, error_code="TIMEOUT")


class CancelledError(PermanentError):
    """请求或操作已被取消（context.cancelled）。"""
    def __init__(self, message: str = "operation cancelled") -> None:
        super().__init__(message, error_code="CANCELLED")

