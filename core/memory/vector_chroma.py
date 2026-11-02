"""ChromaDB 实现。"""

import os

import chromadb

from config import CHROMA_DIR, CHROMA_COLLECTION
from core.embedding import embed as embed_texts
from core.memory.vector_store import VectorStore
from logger import log_event


class ChromaVectorStore(VectorStore):
    def __init__(self):
        os.makedirs(CHROMA_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(path=CHROMA_DIR)
        self._collection = self._client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        log_event("info", "ChromaDB 初始化",
                  stage="memory", event="vector.chroma.init",
                  extra={"path": CHROMA_DIR,
                         "count": self._collection.count()})

    def add(self, ids, contents, metadatas):
        if not ids:
            return
        vectors = embed_texts(contents)
        self._collection.add(
            ids=[str(i) for i in ids],
            embeddings=vectors,
            documents=contents,
            metadatas=metadatas,
        )

    def search(self, query, top_k=3, where=None):
        vec = embed_texts([query])[0]
        kwargs = {"query_embeddings": [vec], "n_results": top_k}
        if where:
            kwargs["where"] = where

        try:
            result = self._collection.query(**kwargs)
        except Exception as e:
            log_event("warning", f"Chroma 检索失败: {e}",
                      stage="memory", event="vector.chroma.error")
            return []

        items = []
        if not result.get("ids") or not result["ids"][0]:
            return items
        for i, cid in enumerate(result["ids"][0]):
            items.append({
                "id": int(cid),
                "content": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                # cosine distance = 1 - cosine similarity
                "score": 1.0 - result["distances"][0][i],
            })
        return items

    def delete(self, ids):
        if not ids:
            return
        self._collection.delete(ids=[str(i) for i in ids])