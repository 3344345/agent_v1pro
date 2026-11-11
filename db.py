"""
兼容层：保留 V1 的 import 路径，内部转发到 core.memory。
main.py 不用改。
"""

from core.memory import get_store
from core.context_builder import build_focus_context


def init_db():
    get_store().init()


def clear_focus():
    get_store().clear_session()


def get_focus() -> dict:
    return get_store().get_session()


def update_focus(**fields):
    get_store().update_session(**fields)


def append_turn(*args, **kwargs):
    """已弃用。历史记录由 logger 统一写入 agent.jsonl。"""
    pass


def get_recent_turns(limit=10) -> list:
    return get_store().get_recent_turns(limit=limit)


def focus_to_context(max_result: int = 800) -> str:
    return build_focus_context(get_store(), max_result=max_result)