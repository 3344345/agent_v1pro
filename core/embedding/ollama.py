"""
Ollama 的 embedding 实现（HTTP API）。

依赖本地 Ollama 服务及其拉取的向量模型（如 bge-m3）。
"""

import os
from config import OLLAMA_URL
from core.embedding.base import Embedder
from core.llm.ollama import OllamaBackend
from logger import log_event


class OllamaEmbedder(Embedder):
    def __init__(self):
        self.backend = OllamaBackend(base_url=OLLAMA_URL)
        # 优先从环境变量或 config 读取，默认 bge-m3
        self.model = os.environ.get("EMBED_MODEL", "bge-m3")
        self._dim = None

    def embed(self, texts):
        if not texts:
            return []
            
        if isinstance(texts, str):
            texts = [texts]

        # 调用 OllamaBackend 里的 embed 接口
        embeddings = self.backend.embed(self.model, texts)
        if not embeddings:
            log_event("error", f"Ollama Embedding 失败，模型: {self.model}", stage="memory")
            return []

        # 第一次请求时，动态获取向量维度（通常是 1024）
        if self._dim is None:
            self._dim = len(embeddings[0])
            log_event("info", f"Ollama Embedding 维度确认: {self._dim}", stage="memory")

        return embeddings

    def dimension(self) -> int:
        if self._dim is None:
            # 如果还没算过，给个默认值兜底（bge-m3 是 1024）
            return 1024
        return self._dim

    def is_available(self) -> bool:
        return self.backend.is_available()