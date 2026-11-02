"""占位：llamacpp_direct 后端尚未实现（批 6）"""
from core.llm.base import LLMBackend


class LlamaCppDirectBackend(LLMBackend):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("llamacpp_direct 后端尚未实现（批 6）")

    def chat(self, *args, **kwargs):
        raise NotImplementedError

    def embed(self, *args, **kwargs):
        raise NotImplementedError

    def is_available(self) -> bool:
        return False
