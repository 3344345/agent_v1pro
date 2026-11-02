"""占位：FreeToken 后端尚未实现（批 10）"""
from core.llm.base import LLMBackend


class FreeTokenBackend(LLMBackend):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("FreeToken 后端尚未实现（批 10）")

    def chat(self, *args, **kwargs):
        raise NotImplementedError

    def embed(self, *args, **kwargs):
        raise NotImplementedError

    def is_available(self) -> bool:
        return False
