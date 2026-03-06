"""
长期记忆：可插拔存储（File / SQLite）、Observer 抽取规则、MemoryService 高层 API。
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from src.infrastructure.observability import emit_audit_event

logger = logging.getLogger(__name__)

# 默认 namespace，与 build_system_context / observe 使用的键一致
PROFILE_NAMESPACE = "profile"
MAX_SYSTEM_PROMPT_VALUE_LEN = 80


def _sanitize_prompt_value(value: Any) -> str:
    """
    将记忆值清洗为可安全拼接到 system prompt 的单行文本。
    """
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("\r", " ").replace("\n", " ")
    text = text.replace("{", "(").replace("}", ")")
    text = text.replace("`", "")
    text = re.sub(r"\s+", " ", text)
    if len(text) > MAX_SYSTEM_PROMPT_VALUE_LEN:
        text = f"{text[:MAX_SYSTEM_PROMPT_VALUE_LEN]}..."
    return text


class MemoryObserver(Protocol):
    """从用户输入中抽取记忆并写回 snapshot 的观察器。"""

    def apply(self, snapshot: Dict[str, Any], user_input: str) -> List[str]:
        """修改 snapshot（通常为 profile 字典），返回本次变更的 key 列表。"""
        ...


class BaseMemoryStore(ABC):
    """记忆存储抽象：支持全量 load/save 与可选的 namespace+key 读写。"""

    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """读取全量快照，结构为 {namespace: {key: value}}。"""
        raise NotImplementedError

    @abstractmethod
    def save(self, data: Dict[str, Any]) -> None:
        """写入全量快照。"""
        raise NotImplementedError

    def get(self, namespace: str, key: str) -> Any:
        """按 namespace 与 key 读取单条；默认实现基于 load。"""
        data = self.load()
        return (data.get(namespace) or {}).get(key)

    def set(self, namespace: str, key: str, value: Any) -> None:
        """按 namespace 与 key 写入单条；默认实现基于 load + save。"""
        data = self.load()
        if namespace not in data:
            data[namespace] = {}
        data[namespace][key] = value
        self.save(data)


class FileMemoryStore(BaseMemoryStore):
    """基于 JSON 文件的存储；兼容旧版扁平结构（自动迁移为 profile 命名空间）。"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def load(self) -> Dict[str, Any]:
        if not self.file_path.exists():
            return {}
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "memory_file_load_failed path=%s error=%s",
                self.file_path,
                exc,
            )
            return {}
        return self._normalize(data)

    def _normalize(self, data: Dict[str, Any] | Any) -> Dict[str, Any]:
        """将旧版扁平结构迁移为 {profile: {key: value}}。"""
        if not isinstance(data, dict):
            return {}
        if not data:
            return {}
        if PROFILE_NAMESPACE in data and isinstance(data[PROFILE_NAMESPACE], dict):
            return data
        profile_keys = ("user_name", "preferred_language", "timezone")
        if any(k in data for k in profile_keys):
            profile = {k: data[k] for k in profile_keys if k in data}
            return {**data, PROFILE_NAMESPACE: profile}
        return data

    def save(self, data: Dict[str, Any]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with self.file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class SQLiteMemoryStore(BaseMemoryStore):
    """基于 SQLite 的存储；表 memory_items(namespace, key, value_json, updated_at)。"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_items (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (namespace, key)
                )
                """
            )

    def load(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        with sqlite3.connect(str(self.db_path)) as conn:
            for row in conn.execute(
                "SELECT namespace, key, value_json FROM memory_items"
            ).fetchall():
                ns, key, value_json = row
                if ns not in result:
                    result[ns] = {}
                try:
                    result[ns][key] = json.loads(value_json)
                except (json.JSONDecodeError, TypeError):
                    result[ns][key] = value_json
        return result

    def save(self, data: Dict[str, Any]) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM memory_items")
            for namespace, kv in data.items():
                if not isinstance(kv, dict):
                    continue
                for key, value in kv.items():
                    value_json = json.dumps(value, ensure_ascii=False)
                    conn.execute(
                        """
                        INSERT INTO memory_items (namespace, key, value_json)
                        VALUES (?, ?, ?)
                        """,
                        (namespace, key, value_json),
                    )
            conn.commit()

    def get(self, namespace: str, key: str) -> Any:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT value_json FROM memory_items WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return row[0]

    def set(self, namespace: str, key: str, value: Any) -> None:
        value_json = json.dumps(value, ensure_ascii=False)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO memory_items (namespace, key, value_json)
                VALUES (?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET value_json = ?, updated_at = datetime('now')
                """,
                (namespace, key, value_json, value_json),
            )
            conn.commit()


# ---------- Observers ----------


class NameObserver:
    """从输入中抽取用户名字。"""

    def apply(self, snapshot: Dict[str, Any], user_input: str) -> List[str]:
        profile = snapshot.setdefault(PROFILE_NAMESPACE, {})
        name_patterns = [
            r"我叫\s*([^\s，。,\.!！?？]+)",
            r"以后叫我\s*([^\s，。,\.!！?？]+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, user_input)
            if match:
                name = match.group(1)
                if profile.get("user_name") != name:
                    profile["user_name"] = name
                    return ["user_name"]
                return []
        return []


class LanguageObserver:
    """从输入中抽取语言偏好。"""

    def apply(self, snapshot: Dict[str, Any], user_input: str) -> List[str]:
        profile = snapshot.setdefault(PROFILE_NAMESPACE, {})
        changed = []
        if "请用中文" in user_input or "用中文回答" in user_input:
            if profile.get("preferred_language") != "中文":
                profile["preferred_language"] = "中文"
                changed.append("preferred_language")
        elif "please answer in english" in user_input.lower():
            if profile.get("preferred_language") != "English":
                profile["preferred_language"] = "English"
                changed.append("preferred_language")
        return changed


class TimezoneObserver:
    """从输入中抽取时区偏好。"""

    def apply(self, snapshot: Dict[str, Any], user_input: str) -> List[str]:
        profile = snapshot.setdefault(PROFILE_NAMESPACE, {})
        patterns = [
            r"(?:我的时区是|时区是)\s*([A-Za-z_/\-+0-9:]+)",
            r"(?:my timezone is)\s*([A-Za-z_/\-+0-9:]+)",
            r"\b(UTC[+-]\d{1,2}(?::\d{2})?)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, user_input, flags=re.IGNORECASE)
            if not match:
                continue
            timezone = match.group(1)
            if profile.get("timezone") != timezone:
                profile["timezone"] = timezone
                return ["timezone"]
            return []
        return []


# ---------- MemoryService ----------


@dataclass
class MemoryService:
    """
    长期记忆服务：通过 Observer 从用户输入抽取记忆并持久化；构建 system 上下文注入 prompt。
    """

    store: BaseMemoryStore
    observers: List[MemoryObserver] = None

    def __post_init__(self) -> None:
        if self.observers is None:
            self.observers = [NameObserver(), LanguageObserver(), TimezoneObserver()]

    def load_snapshot(self) -> Dict[str, Any]:
        return self.store.load()

    def build_system_context(self) -> str:
        snapshot = self.load_snapshot()
        profile = snapshot.get(PROFILE_NAMESPACE) or {}
        user_name = _sanitize_prompt_value(profile.get("user_name"))
        preferred_language = _sanitize_prompt_value(profile.get("preferred_language"))
        timezone = _sanitize_prompt_value(profile.get("timezone"))
        parts = []
        if user_name:
            parts.append(f"用户名字是 {user_name}。")
        if preferred_language:
            parts.append(f"用户偏好语言是 {preferred_language}。")
        if timezone:
            parts.append(f"用户时区是 {timezone}。")
        return " ".join(parts)

    def observe_user_input(self, user_input: str) -> Dict[str, Any]:
        snapshot = self.load_snapshot()
        if PROFILE_NAMESPACE not in snapshot:
            snapshot[PROFILE_NAMESPACE] = {}
        changed: List[str] = []
        for observer in self.observers:
            changed.extend(observer.apply(snapshot, user_input))
        deduped_changed = list(dict.fromkeys(changed))
        if deduped_changed:
            self.store.save(snapshot)
            logger.info("memory_updated fields=%s", deduped_changed)
            emit_audit_event(
                "memory_updated",
                actor="MemoryService",
                payload={"fields": deduped_changed, "input_len": len(user_input)},
            )
        return snapshot

    def get_user_profile(self) -> Dict[str, Any]:
        """返回 profile 命名空间下的键值，便于上层直接使用。"""
        snapshot = self.load_snapshot()
        return dict(snapshot.get(PROFILE_NAMESPACE) or {})
