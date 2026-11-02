"""
MemoryStore 抽象。

职责：只负责持久化。
不负责：LLM 调用（那是 compressor.py 的事）、拼 prompt（context_builder.py）。

扩展位：search / save / kv_ref 现在只声明签名，批 7/8 实现。
"""

from abc import ABC, abstractmethod


class MemoryStore(ABC):

    # ========== 生命周期 ==========
    @abstractmethod
    def init(self) -> None:
        """初始化表结构（幂等）"""
        pass

    # ========== session ==========
    @abstractmethod
    def clear_session(self) -> None:
        """清空 session + turn_history + task_summaries"""
        pass

    @abstractmethod
    def get_session(self) -> dict:
        """返回 session 单行，空时返回 {}"""
        pass

    @abstractmethod
    def update_session(self, **fields) -> None:
        """更新 session 指定字段"""
        pass

    # ========== turn_history ==========
    @abstractmethod
    def append_turn(self, user_input, intent_summary,
                    tool=None, tool_args=None, result=None,
                    status="done") -> None:
        """追加一轮历史，超出 TURN_HISTORY_MAX 自动裁剪最老的"""
        pass

    @abstractmethod
    def get_recent_turns(self, limit: int = 12,
                         only_unsummarized: bool = True) -> list:
        """
        按时间正序返回最近 N 轮。

        only_unsummarized=True  → 只返回未被压缩的（上下文用）
        only_unsummarized=False → 所有轮次（任务锚点用）
        """
        pass

    # ========== 上下文压缩 ==========
    @abstractmethod
    def get_unsummarized_turns(self) -> list:
        """返回所有未压缩的轮次（正序）"""
        pass

    @abstractmethod
    def mark_turns_summarized(self, turn_ids: list) -> None:
        """标记轮次已压缩"""
        pass

    @abstractmethod
    def save_summary(self, summary: str, covers_turn_ids: list,
                     session_id: str = None) -> int:
        """保存摘要，返回摘要 id"""
        pass

    @abstractmethod
    def get_summaries(self) -> list:
        """返回所有摘要（按时间正序）"""
        pass


    # ========== memories（批 8 起实现） ==========
    def save(self, category, content, source=None, trigger=None,
             inject=0, static=0, scope="global") -> int:
        raise NotImplementedError("memories 写入尚未实现")

    def search(self, query, categories=None, top_k=None,
               min_score=None) -> list:
        raise NotImplementedError("向量检索尚未实现")

    def get_preferences(self, scope: str = "global") -> list:
        raise NotImplementedError("preference 读取尚未实现")

    def save_kv_ref(self, session_id: str, file_path: str,
                    model_hash: str) -> None:
        raise NotImplementedError("KV 快照将在批 7 实现")

    def get_kv_ref(self, session_id: str, model_hash: str) -> dict:
        raise NotImplementedError("KV 快照将在批 7 实现")

    def list_all(self, categories=None, limit=100) -> list:
        raise NotImplementedError("memories 列出尚未实现")

    def get(self, memory_id: int):
        raise NotImplementedError("memories 读取尚未实现")

    def delete(self, memory_id: int) -> bool:
        raise NotImplementedError("memories 删除尚未实现")