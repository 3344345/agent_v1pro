from registries.tool_registry import register
from core import search
from tools.context import get_context


@register(
    name="web_search",
    description=(
        "搜索信息。\n\n"
        "【默认，不填 source】用 Parallel 通用搜索。**绝大多数情况都用这个**。\n"
        "适用范围：搜任何信息、找任何东西，包括"
        "\"搜一下 X 的 GitHub 仓库\"、\"查一下 XXX 是什么\"、\"看看 XXX 新闻\"。\n\n"
        "【source='searxng'】只在用户明确说\"**在某个网站上搜**\"时用。\n"
        "判断标准：用户想限定搜索范围在某个具体站点内。\n"
        "这时 query 里必须加 site:域名。\n\n"
        "正确示例：\n"
        "- 用户：搜一下 Python 3.12 新特性\n"
        "  → web_search(query='Python 3.12 新特性')\n"
        "- 用户：搜一下 UxPlay 的 GitHub 仓库\n"
        "  → web_search(query='UxPlay GitHub repository')    ← 通用搜索，不填 source\n"
        "- 用户：在 GitHub 上搜 UxPlay\n"
        "  → web_search(query='UxPlay site:github.com', source='searxng')\n"
        "- 用户：看看 B 站上 Python 教程\n"
        "  → web_search(query='Python 教程 site:bilibili.com', source='searxng')\n"
        "- 用户：知乎上怎么评价 XXX\n"
        "  → web_search(query='评价 XXX site:zhihu.com', source='searxng')\n\n"
        "错误用法（不要这样）：\n"
        "- ❌ 用户说\"搜一下 X 的 GitHub 仓库\"就填 source='searxng'——这只是找信息，不是限定在站内搜"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "source": {
                "type": "string",
                "description": "可选。不填=Parallel通用搜索（默认，推荐）；searxng=只在用户明确说'在某网站上搜'时用（query 需带 site:域名）",
            },
        },
        "required": ["query"],
    },
    requires_network=True,
)
def web_search(query: str, source: str = None) -> str:
    if not query or not query.strip():
        return "❌ 未提供搜索关键词"

    results, used_source = search.search(query, source_hint=source)
    if not results:
        return f"无相关结果（来源: {used_source}）"

    # 存结构化结果，供主循环写入 focus.artifacts
    get_context().last_search_results = results

    return search.format_results(results, used_source)