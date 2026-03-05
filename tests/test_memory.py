"""Memory 层单元测试：Store、Observer、MemoryService。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.agent.memory import (
    PROFILE_NAMESPACE,
    FileMemoryStore,
    LanguageObserver,
    MemoryService,
    NameObserver,
    SQLiteMemoryStore,
)


class TestNameObserver(unittest.TestCase):
    def test_extract_name(self) -> None:
        snap: dict = {PROFILE_NAMESPACE: {}}
        o = NameObserver()
        self.assertEqual(o.apply(snap, "我叫张三"), ["user_name"])
        self.assertEqual(snap[PROFILE_NAMESPACE]["user_name"], "张三")

    def test_extract_name_later_call(self) -> None:
        snap = {PROFILE_NAMESPACE: {"user_name": "李四"}}
        o = NameObserver()
        self.assertEqual(o.apply(snap, "以后叫我王五"), ["user_name"])
        self.assertEqual(snap[PROFILE_NAMESPACE]["user_name"], "王五")


class TestLanguageObserver(unittest.TestCase):
    def test_extract_chinese(self) -> None:
        snap = {PROFILE_NAMESPACE: {}}
        o = LanguageObserver()
        self.assertEqual(o.apply(snap, "请用中文回答"), ["preferred_language"])
        self.assertEqual(snap[PROFILE_NAMESPACE]["preferred_language"], "中文")

    def test_extract_english(self) -> None:
        snap = {PROFILE_NAMESPACE: {}}
        o = LanguageObserver()
        self.assertEqual(o.apply(snap, "please answer in english"), ["preferred_language"])
        self.assertEqual(snap[PROFILE_NAMESPACE]["preferred_language"], "English")


class TestFileMemoryStore(unittest.TestCase):
    def test_load_missing_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            store = FileMemoryStore(str(Path(d) / "nonexistent.json"))
            self.assertEqual(store.load(), {})

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "mem.json"
            store = FileMemoryStore(str(path))
            data = {PROFILE_NAMESPACE: {"user_name": "Test", "preferred_language": "中文"}}
            store.save(data)
            self.assertEqual(store.load(), data)


class TestSQLiteMemoryStore(unittest.TestCase):
    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "mem.db"
            store = SQLiteMemoryStore(str(db))
            data = {PROFILE_NAMESPACE: {"user_name": "SQLiteUser", "preferred_language": "English"}}
            store.save(data)
            self.assertEqual(store.load(), data)

    def test_get_set(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "mem.db"
            store = SQLiteMemoryStore(str(db))
            self.assertIsNone(store.get(PROFILE_NAMESPACE, "user_name"))
            store.set(PROFILE_NAMESPACE, "user_name", "Alice")
            self.assertEqual(store.get(PROFILE_NAMESPACE, "user_name"), "Alice")


class TestMemoryService(unittest.TestCase):
    def test_observe_and_build_context_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "mem.json"
            store = FileMemoryStore(str(path))
            svc = MemoryService(store=store)
            svc.observe_user_input("我叫小明，请用中文回答。")
            ctx = svc.build_system_context()
            self.assertIn("小明", ctx)
            self.assertIn("中文", ctx)

    def test_observe_and_build_context_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "mem.db"
            store = SQLiteMemoryStore(str(db))
            svc = MemoryService(store=store)
            svc.observe_user_input("我叫小红，please answer in english")
            ctx = svc.build_system_context()
            self.assertIn("小红", ctx)
            self.assertIn("English", ctx)


if __name__ == "__main__":
    unittest.main()
