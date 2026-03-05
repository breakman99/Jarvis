from __future__ import annotations

from typing import Any

from ..tools import ToolRegistry


class ToolSet:
    """Agent 可见工具子集视图。"""

    def __init__(self, registry: ToolRegistry, allowed_names: list[str] | None = None):
        self._registry = registry
        self._allowed = set(allowed_names) if allowed_names else None

    def to_openai_tools(self) -> list[dict[str, Any]]:
        if self._allowed is None:
            return self._registry.to_openai_tools()
        return [
            tool.spec.to_openai_schema()
            for tool in self._registry.list_tools()
            if tool.name in self._allowed
        ]
