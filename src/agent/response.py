from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentResponse:
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    steps: List[str] = field(default_factory=list)

