"""
LLM 后端抽象基类。

核心能力（必须实现）：chat / embed / is_available
扩展能力（可选）：save_state / load_state / kv_cache_info / reset_cache

能力声明规范：
    子类通过类属性 SUPPORTED 声明自己支持的扩展能力。
    调用方用 backend.supports("save_state") 判断，不要用 try/except。

    例：
        class LlamaCppDirect(LLMBackend):
            SUPPORTED = {"save_state", "load_state", "kv_cache_info", "reset_cache"}

        class OllamaBackend(LLMBackend):
            SUPPORTED = set()   # 全部不支持

    未声明的能力，调用对应方法会抛 NotImplementedError。

返回格式（chat）：
    {
        "message": {"content": "...", "tool_calls": [...]},
        "done_reason": "stop" | "length" | "tool_calls",
        "eval_count": int,
        "prompt_eval_count": int,
    }
    或 {"error": "..."}
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMBackend(ABC):
    # 子类覆盖；基类默认为空
    SUPPORTED: set = set()

    # ========== 核心能力 ==========
    @abstractmethod
    def chat(self, model: str, messages: list,
             tools: Optional[list] = None,
             options: Optional[dict] = None,
             timeout: Optional[int] = None) -> dict:
        """对话调用。返回统一格式，或 {"error": "..."}"""
        pass

    @abstractmethod
    def embed(self, model: str, texts: list) -> list:
        """向量化。返回 list[list[float]]"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """健康检查"""
        pass

    # ========== 扩展能力（默认不支持） ==========
    def save_state(self, path: str) -> None:
        raise NotImplementedError(f"{self.__class__.__name__} 不支持 save_state")

    def load_state(self, path: str) -> None:
        raise NotImplementedError(f"{self.__class__.__name__} 不支持 load_state")

    def kv_cache_info(self) -> dict:
        raise NotImplementedError(f"{self.__class__.__name__} 不支持 kv_cache_info")

    def reset_cache(self) -> None:
        raise NotImplementedError(f"{self.__class__.__name__} 不支持 reset_cache")

    # ========== 中断 ==========
    def abort_current(self) -> None:
        """中断正在进行的调用。

        默认 no-op。
        有中断能力的后端（HTTP 后端关 session；direct 后端真 stop）覆盖它。
        调用方通过 supports("interrupt") 判断能力，不通过这个方法的存在性。
        """
        pass

    # ========== 资源释放 ==========
    def close(self) -> None:
        """释放资源（HTTP session 等）。默认无操作。"""
        pass

    # ========== 能力查询 ==========
    def supports(self, capability: str) -> bool:
        """查询是否支持某个扩展能力"""
        return capability in self.SUPPORTED