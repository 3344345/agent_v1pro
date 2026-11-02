"""
记忆层统一入口。
"""

from typing import Optional

from core.memory.base import MemoryStore

_store: Optional[MemoryStore] = None


def get_store() -> MemoryStore:
    global _store
    if _store is None:
        from core.memory.sqlite_store import SqliteMemoryStore
        _store = SqliteMemoryStore()
    return _store


def reset_store() -> None:
    global _store
    _store = None