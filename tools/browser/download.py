import os
from registries.tool_registry import register
from core import browser
from logger import log_event
from config import BROWSER_TIMEOUT

@register(
    name="browser_download",
    description=(
        "【浏览器下载原语】触发下载并强制阻塞等待文件完全落盘。\n"
        "内部使用 Playwright 的并发原语 (expect_download)，完美避免事件丢失。\n"
        "你可以传入真实的 URL 直链作为 trigger，或者传入网页按钮的 CSS 选择器。\n"
        "⚠️ 注意：如果已知直链，优先用 execute_command 跑 curl！此工具仅用于必须通过浏览器点击触发的场景。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "trigger": {
                "type": "string", 
                "description": "触发方式：以 http/https 开头视为直链（会自动创建 a 标签点击）；否则视为 CSS 选择器（如 'text=Download'）"
            },
            "save_path": {
                "type": "string", 
                "description": "最终保存的绝对路径（包含文件名），如 /home/user/Desktop/vscode.deb"
            },
            "timeout": {
                "type": "integer", 
                "description": "等待下载完成的最大超时时间（秒），默认 1800（30分钟）。"
            }
        },
        "required": ["trigger", "save_path"]
    },
    requires_network=True,
)
def browser_download(trigger: str, save_path: str, timeout: int = 1800) -> str:
    save_path = os.path.expanduser(save_path)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    # 🚨 防呆：拦截泛型标签
    if not (trigger.startswith("http://") or trigger.startswith("https://")):
        if trigger.strip() in ("a", "button", "div", "a, button", "*"):
            return "❌ [系统拦截] 禁止使用泛型标签（如 'a' 或 'button'）作为下载触发器！这无法精准命中下载按钮。请先用 browser_snapshot(interactive_only=True) 找准确的按钮类名或文本。"

    try:
        page = browser._get_page()
        original_timeout = BROWSER_TIMEOUT
        page.set_default_timeout(timeout * 1000)
        
        log_event("info", f"准备触发下载: {trigger}", stage="tool_call", console="📥 正在尝试触发下载事件...")

        # 🚨 防呆：触发事件监听上限设为 15 秒
        TRIGGER_TIMEOUT_MS = 15000 
        
        try:
            with page.expect_download(timeout=TRIGGER_TIMEOUT_MS) as download_info:
                if trigger.startswith("http"):
                    page.evaluate(f"() => {{ const a = document.createElement('a'); a.href = '{trigger}'; a.download = ''; document.body.appendChild(a); a.click(); a.remove(); }}")
                else:
                    page.locator(trigger).first.click()
        except Exception as e:
            if "Timeout" in str(e) or "timeout" in str(e):
                return "❌ [触发失败] 点击了元素，但 15 秒内浏览器没有触发任何下载行为！请确认你选中的是不是真正的下载按钮。严禁盲目重试！"
            raise e
        
        download = download_info.value
        filename = download.suggested_filename
        
        log_event("info", f"检测到下载开始: {filename}，阻塞写入...", stage="tool_call", console=f"⏳ 正在落盘: {filename} (大文件请耐心等待，不要打断)...")
        
        # 真正阻塞的地方
        download.save_as(save_path)
        
        size_bytes = os.path.getsize(save_path)
        size_mb = size_bytes / (1024 * 1024)
        return f"✅ [下载完成] 路径: {save_path}\n大小: {size_mb:.2f} MB\n\n请立刻调用 `file {save_path}` 校验文件类型。"
        
    except Exception as e:
        return f"❌ 下载失败: {e}"
    finally:
        try: page.set_default_timeout(original_timeout)
        except: pass