"""Embedding 后端抽象。"""

from abc import ABC, abstractmethod


class Embedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化。返回 list[list[float]]"""
        pass

    @abstractmethod
    def dimension(self) -> int:
        """向量维度"""
        pass

    def is_available(self) -> bool:
        return True