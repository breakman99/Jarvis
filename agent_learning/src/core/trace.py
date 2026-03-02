from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TraceEvent:
    step: int
    kind: str
    payload: dict[str, Any]


@dataclass
class TraceLogger:
    events: list[TraceEvent] = field(default_factory=list)

    def add(self, step: int, kind: str, payload: dict[str, Any]) -> None:
        self.events.append(TraceEvent(step=step, kind=kind, payload=payload))

    def as_dicts(self) -> list[dict[str, Any]]:
        return [
            {"step": event.step, "kind": event.kind, "payload": event.payload}
            for event in self.events
        ]

    def dump_json(self, path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(self.as_dicts(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
