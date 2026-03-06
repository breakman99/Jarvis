"""
兼容层：错误类型已迁移到 `src.domain.common.errors`。
"""

from src.domain.common.errors import (
    CancelledError,
    JarvisError,
    PermanentError,
    TimeoutError,
    TransientError,
)

__all__ = [
    "JarvisError",
    "TransientError",
    "PermanentError",
    "TimeoutError",
    "CancelledError",
]

