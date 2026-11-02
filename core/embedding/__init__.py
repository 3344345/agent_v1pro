"""Embedding 统一入口。"""
from config import EMBED_BACKEND
from core.embedding.base import Embedder

_embedder = None

def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        if EMBED_BACKEND == "llamacpp_direct":
            from core.embedding.llamacpp_direct import LlamaCppDirectEmbedder
            _embedder = LlamaCppDirectEmbedder()
        elif EMBED_BACKEND == "llamacpp_server":
            from core.embedding.llamacpp_server import LlamaCppServerEmbedder
            _embedder = LlamaCppServerEmbedder()
        elif EMBED_BACKEND == "ollama":
            from core.embedding.ollama import OllamaEmbedder
            _embedder = OllamaEmbedder()
        elif EMBED_BACKEND == "fastembed":
            from core.embedding.fastembed import FastEmbedder
            _embedder = FastEmbedder()
        else:
            raise ValueError(f"未知 embedding 后端: {EMBED_BACKEND}")
    return _embedder

def embed(texts):
    return get_embedder().embed(texts)

def dimension():
    return get_embedder().dimension()