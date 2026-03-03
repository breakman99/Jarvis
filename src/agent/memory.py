from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any, Dict


class BaseMemoryStore(ABC):
    @abstractmethod
    def load(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def save(self, data: Dict[str, Any]) -> None:
        raise NotImplementedError


class FileMemoryStore(BaseMemoryStore):
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def load(self) -> Dict[str, Any]:
        if not self.file_path.exists():
            return {}
        with self.file_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: Dict[str, Any]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


@dataclass
class MemoryService:
    store: BaseMemoryStore

    def load_snapshot(self) -> Dict[str, Any]:
        return self.store.load()

    def build_system_context(self) -> str:
        snapshot = self.load_snapshot()
        user_name = snapshot.get("user_name")
        preferred_language = snapshot.get("preferred_language")

        parts = []
        if user_name:
            parts.append(f"用户名字是 {user_name}。")
        if preferred_language:
            parts.append(f"用户偏好语言是 {preferred_language}。")
        return " ".join(parts)

    def observe_user_input(self, user_input: str) -> Dict[str, Any]:
        snapshot = self.load_snapshot()
        updated = False

        name_patterns = [
            r"我叫\s*([^\s，。,\.!！?？]+)",
            r"以后叫我\s*([^\s，。,\.!！?？]+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, user_input)
            if match:
                snapshot["user_name"] = match.group(1)
                updated = True
                break

        if "请用中文" in user_input or "用中文回答" in user_input:
            snapshot["preferred_language"] = "中文"
            updated = True
        elif "please answer in english" in user_input.lower():
            snapshot["preferred_language"] = "English"
            updated = True

        if updated:
            self.store.save(snapshot)

        return snapshot

