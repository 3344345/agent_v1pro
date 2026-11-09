from registries.tool_registry import register
from core import browser

@register(
    name="browser_snapshot",
    description=(
        "获取当前页面的标题、URL 和可见文本。用于阅读页面内容。\n"
        "如果页面交互元素很多导致文本混乱，可设 interactive_only=true，系统将只返回输入框、按钮等交互元素的结构（极利于寻找搜索框）。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "max_chars": {
                "type": "integer",
                "description": "文本截断长度，默认 1500。",
            },
            "interactive_only": {
                "type": "boolean",
                "description": "是否只提取可交互的元素（按钮、输入框）。找搜索框时极为有用。"
            }
        },
    },
    requires_network=True,
)
def browser_snapshot(max_chars: int = 1500, interactive_only: bool = False) -> str:
    max_chars = max(500, min(max_chars, 5000))
    try:
        page = browser._get_page()
        title = page.title()
        url = page.url
        
        if interactive_only:
            js = """
            () => {
                const els = Array.from(document.querySelectorAll('input, button, a, textarea, select, [role="button"]'));
                return els.map(el => {
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id,
                        class: (typeof el.className === 'string' ? el.className : '').slice(0, 30),
                        placeholder: el.placeholder || '',
                        text: (el.innerText || '').slice(0, 20).trim(),
                        visible: !!(el.offsetWidth || el.offsetHeight)
                    }
                }).filter(el => el.visible);
            }
            """
            els = page.evaluate(js)
            lines = []
            for el in els[:80]: # 限制数量防爆
                desc = f"- <{el['tag']}"
                if el['id']: desc += f" id='{el['id']}'"
                if el['class']: desc += f" class='{el['class']}'"
                if el['placeholder']: desc += f" placeholder='{el['placeholder']}'"
                if el['text']: desc += f" text='{el['text']}'"
                desc += ">"
                lines.append(desc)
            return f"标题: {title}\nURL: {url}\n可交互元素:\n" + ("\n".join(lines) or "(无)")
            
        # 正常文本模式
        text = page.evaluate(f"() => (document.body ? document.body.innerText : '').slice(0, {max_chars})")
        return f"标题: {title}\nURL: {url}\n内容:\n{text or '(空)'}"
        
    except Exception as e:
        return f"❌ 快照失败: {e}"


@register(
    name="browser_screenshot",
    description=(
        "对当前页面截图，保存到 ~/Pictures/Screenshots/，返回路径。\n"
        "仅用于：1. 用户明确要求截图 2. 页面以图片为主。其他情况优先用 browser_snapshot 读文本。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "保存路径（可选）"}
        },
    },
    requires_network=True,
)
def browser_screenshot(path: str = None) -> str:
    return browser.screenshot(path=path)


@register(
    name="browser_evaluate",
    description=(
        "在页面执行 JavaScript 并返回结果。\n\n"
        "⚠️ 返回值规则：用 return 或直接写表达式；不要用 console.log。\n"
        "⚠️ 如果返回了 DOM 节点，系统会自动将其转义为属性。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "js": {"type": "string", "description": "JavaScript 代码"}
        },
        "required": ["js"],
    },
    requires_network=True,
)
def browser_evaluate(js: str) -> str:
    if not js or not js.strip(): return "❌ 未提供 JS"
    try:
        page = browser._get_page()
        result = page.evaluate(js)
        
        # 核心补丁：拦截不可序列化的 DOM 节点，自动转字典
        if str(result) == "<Node>" or (isinstance(result, dict) and result.get("__node__")):
            attrs = page.evaluate("""
                el => {
                    if (!el) return null;
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id,
                        class: (typeof el.className === 'string' ? el.className : ''),
                        placeholder: el.placeholder || '',
                        value: el.value || '',
                        text: (el.innerText || '').slice(0, 50)
                    }
                }
            """)
            return f"✅ 找到了元素（已自动转义）: {attrs}"
            
        if result is None:
            return "❌ （JS 返回了 None）请直接写表达式获取属性，例如 document.querySelector('...').placeholder"
            
        s = str(result)
        if len(s) > 2000:
            s = s[:2000] + f"\n...[结果已截断，原长度 {len(s)} 字符]"
        return f"✅ 结果: {s}"
        
    except Exception as e:
        return f"❌ JS 异常: {e}"