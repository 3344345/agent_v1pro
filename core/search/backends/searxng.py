import requests
from typing import Optional, Callable

from config import SEARXNG_URL


def _log(log_fn: Optional[Callable], level: str, msg: str):
    if log_fn:
        log_fn(level, msg, stage="tool_call")


def search(query: str, log_fn=None) -> tuple:
    if not query or not query.strip():
        return [], "none"

    try:
        resp = requests.get(
            SEARXNG_URL,
            params={"q": query, "format": "json"},
            timeout=15,
        )
        if resp.status_code != 200:
            _log(log_fn, "warning", f"SearXNG 状态码异常: {resp.status_code}")
            return [], "none"
        data = resp.json()
        results = data.get("results", [])
    except Exception as e:
        _log(log_fn, "warning", f"SearXNG 请求失败: {e}")
        return [], "none"

    if not results:
        _log(log_fn, "warning", f"SearXNG 返回空结果: {query}")
        return [], "none"

    standardized = []
    for r in results[:5]:
        standardized.append({
            "title": r.get("title", "无标题"),
            "content": r.get("content", r.get("snippet", "")),
            "url": r.get("url", ""),
        })

    return standardized, "searxng"