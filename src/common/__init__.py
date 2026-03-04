"""
公共类型：统一错误类（JarvisError、TransientError、TimeoutError、CancelledError 等），
供 LLM 与工具层重试逻辑及上层异常兜底使用。
"""
from .errors import CancelledError, JarvisError, PermanentError, TimeoutError, TransientError

__all__ = [
    "JarvisError",
    "TransientError",
    "PermanentError",
    "TimeoutError",
    "CancelledError",
]

