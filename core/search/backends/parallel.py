import json
import requests
from typing import Optional, Callable


MCP_URL = "https://search.parallel.ai/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def _log(log_fn: Optional[Callable], level: str, msg: str):
    if log_fn:
        log_fn(level, msg, stage="tool_call")


def _raw_post(payload: dict, timeout: int = 30) -> dict:
    r = requests.post(MCP_URL, json=payload, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _initialize(log_fn=None):
    _raw_post({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "clientInfo": {"name": "agent-v1", "version": "1.0.0"},
            "capabilities": {"tools": {}},
        },
    })
    requests.post(
        MCP_URL,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers=HEADERS,
        timeout=10,
    )


def search(query: str, log_fn=None) -> tuple:
    if not query or not query.strip():
        return [], "none"

    try:
        _initialize(log_fn)
        resp = _raw_post({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "web_search",
                "arguments": {
                    "objective": query,
                    "search_queries": [query],
                },
            },
        }, timeout=60)
    except Exception as e:
        _log(log_fn, "warning", f"Parallel Search 请求失败: {e}")
        return [], "none"

    try:
        content = resp.get("result", {}).get("content", [])
        if not content:
            _log(log_fn, "warning", "Parallel Search 返回空 content")
            return [], "none"
        text = content[0].get("text", "")
        inner = json.loads(text)
        raw_results = inner.get("results", [])
    except Exception as e:
        _log(log_fn, "warning", f"Parallel Search 解析失败: {e}")
        return [], "none"

    standardized = []
    for r in raw_results[:5]:
        excerpts = r.get("excerpts", []) or []
        content_text = "\n".join(excerpts)[:500]
        standardized.append({
            "title": r.get("title", "无标题"),
            "content": content_text,
            "url": r.get("url", ""),
        })

    if not standardized:
        _log(log_fn, "warning", f"Parallel Search 无结果: {query}")
        return [], "none"

    return standardized, "parallel"