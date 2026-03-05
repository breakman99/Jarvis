"""
进程内指标收集器：计数（inc）与直方图（observe）。

用于 LLM 调用次数/延迟、工具调用次数/延迟、Orchestrator 迭代等打点；
snapshot() 可导出当前状态，便于对接 Prometheus 或监控系统。
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, Tuple


class MetricsCollector:
    """轻量级进程内指标收集器；线程安全，支持按 labels 区分的计数与直方图。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], int] = defaultdict(int)
        self._histograms: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], list[float]] = defaultdict(list)

    def inc(self, name: str, *, labels: Dict[str, str] | None = None, value: int = 1) -> None:
        """计数器 +value；labels 用于区分维度（如 provider、tool、status）。"""
        key = (name, tuple(sorted((labels or {}).items())))
        with self._lock:
            self._counters[key] += value

    def observe(self, name: str, value: float, *, labels: Dict[str, str] | None = None) -> None:
        """记录直方图样本（如延迟毫秒数）。"""
        key = (name, tuple(sorted((labels or {}).items())))
        with self._lock:
            self._histograms[key].append(value)

    def snapshot(self) -> dict:
        """导出当前计数与直方图，便于上报或调试。"""
        with self._lock:
            return {
                "counters": {f"{k[0]}|{dict(k[1])}": v for k, v in self._counters.items()},
                "histograms": {f"{k[0]}|{dict(k[1])}": list(v) for k, v in self._histograms.items()},
            }


metrics = MetricsCollector()
