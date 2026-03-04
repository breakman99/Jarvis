from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


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
    """
    长期记忆服务：从用户输入中提取结构化记忆并持久化，在对话启动时注入 system prompt。

    设计意图：Orchestrator 在 run 开始时调用 observe_user_input 更新记忆，在构造
    session 时通过 build_system_context 将已知记忆（如 user_name、preferred_language）
    注入系统提示，使 LLM 能利用跨会话信息。协作：由 AgentApp 根据 memory_backend 构造
    并注入 Orchestrator；存储由 BaseMemoryStore 抽象，当前实现为 FileMemoryStore。
    """
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
            changed = []
            if any(re.search(p, user_input) for p in name_patterns):
                changed.append("user_name")
            if "请用中文" in user_input or "用中文回答" in user_input or "please answer in english" in user_input.lower():
                changed.append("preferred_language")
            logger.info("memory_updated fields=%s", changed)

        return snapshot

