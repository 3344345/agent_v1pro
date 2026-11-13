"""ChromaDB 实现（带维度冲突检测）。"""

import os
import sys
import chromadb

from config import CHROMA_DIR, CHROMA_COLLECTION
from core.embedding import embed as embed_texts
from core.memory.vector_store import VectorStore
from logger import log_event


class ChromaVectorStore(VectorStore):
    def __init__(self):
        os.makedirs(CHROMA_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(path=CHROMA_DIR)
        
        try:
            self._collection = self._client.get_or_create_collection(
                name=CHROMA_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            self._handle_dimension_error(e, "初始化")
            raise e

        log_event("info", "ChromaDB 初始化",
                  stage="memory", event="vector.chroma.init",
                  extra={"path": CHROMA_DIR,
                         "count": self._collection.count()})

    def _handle_dimension_error(self, e: Exception, action: str):
        """捕获并吐槽维度不匹配问题"""
        err_msg = str(e).lower()
        
        # 捕获 ChromaDB 的维度不匹配报错 (ValueError 或 InvalidDimensionException)
        if "dimension" in err_msg or "expecting" in err_msg or "invalid" in err_msg:
            print("\n" + "❌" * 25)
            print("🚨 维度冲突警告！")
            print(f"在执行【{action}】时，发现当前数据库里的向量维度与模型输出的维度不匹配！")
            print("你是不是手贱去 .env 里改了 AGENT_EMBED_BACKEND？")
            print(" 我真的求你了，这个我是真的累了，正常人谁会乱改这个，我弄的时候fastembed真的只是为了适配云端API弄的，然后现在搞成这个样子，抱歉")
            print("（注：fastembed 是 512 维，Ollama bge-m3 是 1024 维）")
            print("👉 解决方法 1：把 .env 里的 AGENT_EMBED_BACKEND 改回原来的值。")
            print("👉 解决方法 2：如果你非要换，自己手动执行 rm -rf data/chroma 清空旧账。")
            print("❌" * 25 + "\n")
            
            log_event("error", f"向量维度不匹配 ({action})", stage="memory", extra={"error": str(e)})
            sys.exit(1)
        else:
            # 如果不是维度问题，记录日志并原样抛出
            log_event("error", f"ChromaDB 异常 ({action}): {e}", stage="memory")
            raise e

    def add(self, ids, contents, metadatas):
        if not ids:
            return
        vectors = embed_texts(contents)
        try:
            self._collection.add(
                ids=[str(i) for i in ids],
                embeddings=vectors,
                documents=contents,
                metadatas=metadatas,
            )
        except Exception as e:
            self._handle_dimension_error(e, "写入向量")

    def search(self, query, top_k=3, where=None):
        vec = embed_texts([query])[0]
        kwargs = {"query_embeddings": [vec], "n_results": top_k}
        if where:
            kwargs["where"] = where

        try:
            result = self._collection.query(**kwargs)
        except Exception as e:
            self._handle_dimension_error(e, "检索向量")
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
        try:
            self._collection.delete(ids=[str(i) for i in ids])
        except Exception as e:
            log_event("warning", f"Chroma 删除失败: {e}", stage="memory")