from registries.tool_registry import register
from core import browser

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
    if not selector or not selector.strip():
        return "❌ 未提供选择器"
        
    try:
        page = browser._get_page()
        locator = page.locator(selector).first
        
        # 1. 正常点击 (3秒超时)
        try:
            locator.click(timeout=3000)
            return f"✅ 已点击: {selector}"
        except Exception:
            pass
            
        # 2. 强制点击 (无视遮挡)
        try:
            locator.click(force=True, timeout=3000)
            return f"✅ 已强制点击: {selector} (绕过遮挡)"
        except Exception:
            pass
            
        # 3. 终极降级：JS 注入点击
        js_code = f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (!el) return 'NOT_FOUND';
            el.click();
            return 'CLICKED_BY_JS';
        }})()
        """
        result = page.evaluate(js_code)
        if result == 'CLICKED_BY_JS':
            return f"✅ 已通过 JS 强行点击 {selector}"
        else:
            return f"❌ 无法点击元素: {selector}"
            
    except Exception as e:
        return f"❌ 点击异常: {e}"

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
    if not selector or not selector.strip():
        return "❌ 未提供选择器"
    
    try:
        page = browser._get_page()
        locator = page.locator(selector).first
        
        # 1. 正常填（3秒超时，不行就降级）
        try:
            locator.fill(value, timeout=3000)
            return f"✅ 已填充 {selector}"
        except Exception:
            pass
            
        # 2. 强制填（无视元素被遮挡或隐藏）
        try:
            locator.fill(value, force=True, timeout=3000)
            return f"✅ 已强制填充 {selector} (绕过遮挡/隐藏)"
        except Exception:
            pass
            
        # 3. 终极降级：JS 注入并触发 Vue/React 绑定
        js_code = f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (!el) return 'NOT_FOUND';
            el.focus();
            el.value = {repr(value)};
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return 'FILLED_BY_JS';
        }})()
        """
        result = page.evaluate(js_code)
        if result == 'FILLED_BY_JS':
            return f"✅ 已通过 JS 暴力注入 {selector}"
        else:
            return f"❌ 无法找到元素或注入失败: {selector}"
            
    except Exception as e:
        return f"❌ 填写异常: {e}"


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
    name="browser_visual_click",
    description="【视觉物理点击】基于坐标点击网页。执行时会在页面上生成一个红色光标动画，适用于 OCR 识别后或 DOM 严重拦截的极客场景。",
    parameters={
        "type": "object",
        "properties": {
            "x": {"type": "number", "description": "X 坐标（像素）"},
            "y": {"type": "number", "description": "Y 坐标（像素）"},
        },
        "required": ["x", "y"],
    },
    requires_network=True,
)
def browser_visual_click(x: float, y: float) -> str:
    try:
        page = browser._get_page()
        # 注入高对比度光标（黑底白边，适配明暗网页）
        js_cursor = f"""
        (() => {{
            let cursor = document.getElementById('ai-agent-cursor');
            if (!cursor) {{
                cursor = document.createElement('div');
                cursor.id = 'ai-agent-cursor';
                cursor.style.cssText = 'position:fixed; width:18px; height:18px; background:rgba(0,0,0,0.85); border-radius:50%; z-index:2147483647; pointer-events:none; transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1); box-shadow: 0 2px 8px rgba(0,0,0,0.4); border: 2px solid #ffffff;';
                document.body.appendChild(cursor);
            }}
            // 先移到位置
            cursor.style.left = '{x - 9}px';
            cursor.style.top = '{y - 9}px';
            cursor.style.opacity = '1';
            cursor.style.transform = 'scale(1)';
            
            // 模拟点击动画
            setTimeout(() => {{
                cursor.style.transform = 'scale(0.6)';
                setTimeout(() => {{
                    cursor.style.transform = 'scale(1)';
                    cursor.style.opacity = '0.4'; // 点完变半透明，不挡视线
                }}, 150);
            }}, 450); 
        }})()
        """
        page.evaluate(js_cursor)
        page.wait_for_timeout(550) # 等动画走完
        page.mouse.click(x, y)
        return f"✅ 视觉物理点击坐标: ({x}, {y})"
    except Exception as e:
        return f"❌ 物理点击失败: {e}"