"""
向量库抽象 + 工厂。

设计原则：
- 向量库是"索引"，不是"权威数据源"
- 只存 id + embedding + 最小元数据
- content 存 SQLite，检索后从 SQLite 取
- 向量库挂了可以从 SQLite 重建
"""

from abc import ABC, abstractmethod
from typing import Optional

from config import VECTOR_BACKEND


class VectorStore(ABC):
    @abstractmethod
    def add(self, ids, contents, metadatas) -> None:
        """添加向量。"""
        pass

    @abstractmethod
    def search(self, query, top_k=3, where=None) -> list:
        """检索。返回 [{"id", "content", "metadata", "score"}, ...]"""
        pass

    @abstractmethod
    def delete(self, ids) -> None:
        pass


_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        if VECTOR_BACKEND == "chromadb":
            from core.memory.vector_chroma import ChromaVectorStore
            _store = ChromaVectorStore()
        elif VECTOR_BACKEND == "numpy":
            from core.memory.vector_numpy import NumpyVectorStore
            _store = NumpyVectorStore()
        else:
            raise ValueError(f"未知向量库: {VECTOR_BACKEND}")
    return _store


def reset_vector_store():
    global _store
    _store = None