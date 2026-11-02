from typing import List, Dict


def format_results(results: List[Dict], source: str) -> str:
    if not results:
        return "无相关结果"

    lines = [f"来源: {source}"]
    for i, r in enumerate(results[:5], 1):
        title = r.get("title", "无标题")
        content = r.get("content", "")
        url = r.get("url", "")
        lines.append(f"{i}. {title}")
        if content:
            lines.append(f"   {content[:200]}")
        if url:
            lines.append(f"   {url}")
    return "\n".join(lines)