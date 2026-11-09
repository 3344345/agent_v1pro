from registries.tool_registry import register
from core import browser

@register(
    name="browser_goto",
    description="在浏览器中打开网页。返回页面标题，表示已成功加载。",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "网址，如 https://www.bilibili.com"}
        },
        "required": ["url"],
    },
    requires_network=True,
)
def browser_goto(url: str) -> str:
    return browser.navigate(url or "")

@register(
    name="browser_wait",
    description="等待指定秒数，用于页面异步加载后截图/快照。通常不需要，Playwright 会自动等待。",
    parameters={
        "type": "object",
        "properties": {
            "seconds": {"type": "number", "description": "等待秒数，默认 2"}
        },
    },
    requires_network=True,
)
def browser_wait(seconds: float = 2.0) -> str:
    return browser.wait(seconds=seconds)