from core.search.dispatch import dispatch
from core.search.format import format_results


def search(query, source_hint=None, log_fn=None):
    return dispatch(query, source_hint=source_hint, log_fn=log_fn)


__all__ = ["search", "format_results"]