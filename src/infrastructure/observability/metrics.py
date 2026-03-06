"""
兼容层：metrics 已迁移到 `src.domain.common.observability`。
"""

from src.domain.common.observability import MetricsCollector, metrics

__all__ = ["MetricsCollector", "metrics"]

