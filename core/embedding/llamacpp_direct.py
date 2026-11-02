"""
llama-cpp-python 的 embedding 实现（同进程，CPU 模式）。

模型懒加载：首次 embed 时才加载，避免 Agent 启动就占内存。
"""

import os
import threading

from config import (
    EMBED_MODEL_PATH, EMBED_N_GPU_LAYERS, EMBED_N_CTX,
)
from core.embedding.base import Embedder
from logger import log_event


class LlamaCppDirectEmbedder(Embedder):
    def __init__(self):
        self._llm = None
        self._dim = None
        self._lock = threading.Lock()

    def _ensure_loaded(self):
        if self._llm is not None:
            return
        with self._lock:
            if self._llm is not None:
                return
            from llama_cpp import Llama
            log_event("info", "加载 embedding 模型",
                      stage="memory", event="embed.load",
                      extra={"path": EMBED_MODEL_PATH})
            self._llm = Llama(
                model_path=EMBED_MODEL_PATH,
                embedding=True,
                n_gpu_layers=EMBED_N_GPU_LAYERS,
                n_ctx=EMBED_N_CTX,
                verbose=False,
            )
            self._dim = len(self._llm.embed("probe"))

    def embed(self, texts):
        if not texts:
            return []
        self._ensure_loaded()
        if isinstance(texts, str):
            return [self._llm.embed(texts)]
        return self._llm.embed(texts)

    def dimension(self):
        if self._dim is None:
            self._ensure_loaded()
        return self._dim

    def is_available(self):
        return os.path.exists(EMBED_MODEL_PATH)