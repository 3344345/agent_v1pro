"""
使用 fastembed (ONNX Runtime) 实现轻量级本地 Embedding。
纯 CPU 运行，无需显卡，首次使用会自动下载约 95MB 的微型模型。
"""

from core.embedding.base import Embedder
from logger import log_event

class FastEmbedder(Embedder):
    def __init__(self):
        self._model = None
        self._dim = None
        # 使用支持中文且极小（约 95MB）的模型
        self.model_name = "BAAI/bge-small-zh-v1.5"

    def _ensure_loaded(self):
        if self._model is not None:
            return
        log_event("info", f"正在加载轻量级向量模型: {self.model_name}", stage="memory")
        from fastembed import TextEmbedding
        # fastembed 会自动缓存到 ~/.cache/fastembed
        self._model = TextEmbedding(model_name=self.model_name)
        
        # 试运行一次确定维度 (bge-small-zh 是 512 维)
        probe = list(self._model.embed(["探测"]))[0]
        self._dim = len(probe)
        log_event("info", f"轻量向量模型加载完毕，维度: {self._dim}", stage="memory")

    def embed(self, texts):
        if not texts:
            return []
        if isinstance(texts, str):
            texts = [texts]
        
        self._ensure_loaded()
        # fastembed 返回的是生成器，需要转成 list
        embeddings = list(self._model.embed(texts))
        return [emb.tolist() for emb in embeddings]

    def dimension(self) -> int:
        if self._dim is None:
            self._ensure_loaded()
        return self._dim

    def is_available(self) -> bool:
        return True