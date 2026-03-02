from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.2
    max_steps: int = 6

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("AGENT_TEMPERATURE", "0.2")),
            max_steps=int(os.getenv("AGENT_MAX_STEPS", "6")),
        )
