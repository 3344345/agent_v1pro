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
    name="browser_click",
    description=(
        "点击页面上的元素。选择器支持 CSS 和 Playwright 扩展语法：\n"
        "- CSS: '#submit' 或 'a.video-title'\n"
        "- 文本: 'text=登录'（按元素上的文字点击）\n"
        "- 角色: 'role=button[name=\"搜索\"]'"
    ),
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "选择器"}
        },
        "required": ["selector"],
    },
    requires_network=True,
)
def browser_click(selector: str) -> str:
    return browser.click(selector or "")


@register(
    name="browser_fill",
    description=(
        "向输入框填写内容。选择器支持：\n"
        "- CSS: '#search-input'\n"
        "- placeholder: 'placeholder=搜索'"
    ),
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "输入框选择器"},
            "value": {"type": "string", "description": "要填的内容"},
        },
        "required": ["selector", "value"],
    },
    requires_network=True,
)
def browser_fill(selector: str, value: str) -> str:
    return browser.fill(selector or "", value or "")


@register(
    name="browser_press",
    description="模拟键盘按键，如 'Enter'、'Escape'、'Tab'。常与 browser_fill 配合提交表单。",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "按键名"}
        },
        "required": ["key"],
    },
    requires_network=True,
)
def browser_press(key: str) -> str:
    return browser.press(key or "")


@register(
    name="browser_evaluate",
    description=(
        "在页面执行 JavaScript 并返回结果。\n\n"
        "⚠️ 返回值规则（关键）：\n"
        "- 返回的是 JS 表达式的值，不是 console.log 的输出\n"
        "- 要拿数据，用 return 或直接写表达式；不要用 console.log\n\n"
        "⚠️ 结果会被截断到 2000 字符：\n"
        "- 不要 return 整个页面或大量元素\n"
        "- 在 JS 里先过滤/截断，例如：\n"
        "  正确：return document.title\n"
        "  正确：Array.from(document.querySelectorAll('a')).slice(0, 10).map(a => a.textContent)\n"
        "  错误：document.querySelectorAll('*').forEach(...)  ← 返回海量数据，会撑爆上下文\n\n"
        "用途：\n"
        "- 页面用 browser_snapshot 拿不到内容时（动态渲染、iframe）\n"
        "- 提取特定元素（表格、列表、特定 selector）\n"
        "- 执行点击/滚动等 DOM 操作"
    ),
    parameters={
        "type": "object",
        "properties": {
            "js": {
                "type": "string",
                "description": "JavaScript 代码。用 return 返回数据，结果会截断到 2000 字符"
            }
        },
        "required": ["js"],
    },
    requires_network=True,
)
def browser_evaluate(js: str) -> str:
    result = browser.evaluate(js or "")
    if isinstance(result, str) and result.startswith("（JS 返回了 None）"):
        return f"❌ {result}"

    s = str(result)
    MAX = 2000
    if len(s) > MAX:
        s = s[:MAX] + f"\n...[结果已截断，原长度 {len(s)} 字符]"
    return f"✅ 结果: {s}"


@register(
    name="browser_snapshot",
    description=(
        "获取当前页面的标题、URL 和可见文本。用于阅读页面内容。\n"
        "默认 1500 字。如果内容不够用，可以传更大的 max_chars 读全（最大 5000 字）。\n"
        "如果页面内容很长，只读到你需要的部分就够，不要贪多。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "max_chars": {
                "type": "integer",
                "description": "文本截断长度。普通查看 1500；需要更多内容时可到 5000。",
            }
        },
    },
    requires_network=True,
)
def browser_snapshot(max_chars: int = 1500) -> str:
    return browser.snapshot(max_chars=max_chars)


@register(
    name="browser_screenshot",
    description=(
        "对当前页面截图，保存到 ~/Pictures/Screenshots/，返回路径。\n"
        "仅用于：\n"
        "1. 用户明确要求截图\n"
        "2. 页面以图片/图表为主，browser_snapshot 拿不到内容\n"
        "其他情况优先用 browser_snapshot 读文本。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "保存路径（可选，默认 ~/Pictures/Screenshots/browser_<时间戳>.png）",
            }
        },
    },
    requires_network=True,
)
def browser_screenshot(path: str = None) -> str:
    return browser.screenshot(path=path)


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