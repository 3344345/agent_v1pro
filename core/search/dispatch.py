from typing import List, Dict, Optional, Callable

from config import SEARCH_BACKENDS, SEARCH_SOURCE_ALIASES


_CLIENTS = {}


def _get_client(name: str):
    if name in _CLIENTS:
        return _CLIENTS[name]
    if name == "parallel":
        from core.search.backends import parallel
        _CLIENTS[name] = parallel
    elif name == "searxng":
        from core.search.backends import searxng
        _CLIENTS[name] = searxng
    else:
        raise ValueError(f"未知搜索后端: {name}")
    return _CLIENTS[name]


def _resolve_source(source_hint: Optional[str]) -> Optional[str]:
    if not source_hint:
        return None
    return SEARCH_SOURCE_ALIASES.get(source_hint.strip().lower())


def dispatch(query: str, source_hint: Optional[str] = None,
             log_fn: Optional[Callable] = None) -> tuple:
    if not query or not query.strip():
        return [], "none"

    if source_hint:
        resolved = _resolve_source(source_hint)
        if not resolved:
            if log_fn:
                log_fn("warning", f"未知搜索源: {source_hint}", stage="tool_call")
            return [], "none"
        # 指定的源优先，其余 SEARCH_BACKENDS 作为 fallback
        backends = [resolved] + [b for b in SEARCH_BACKENDS if b != resolved]
    else:
        backends = list(SEARCH_BACKENDS)

    if not backends:
        if log_fn:
            log_fn("warning", "无可用搜索后端", stage="tool_call")
        return [], "none"

    for name in backends:
        try:
            client = _get_client(name)
        except ValueError as e:
            if log_fn:
                log_fn("warning", str(e), stage="tool_call")
            continue

        try:
            results, _ = client.search(query, log_fn=log_fn)
        except Exception as e:
            if log_fn:
                log_fn("warning", f"{name} 异常: {e}", stage="tool_call")
            continue

        if results:
            return results, name

        if log_fn:
            log_fn("info", f"{name} 返回空，尝试下一个", stage="tool_call")

    return [], "none"