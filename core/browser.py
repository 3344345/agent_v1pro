"""
browser 工具后端。Playwright + Chromium。
包含底层自动等待（Auto-Wait）和自动标签页同步。
"""

import os
import time
import subprocess
from typing import Optional, Callable

from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright

from config import (
    CHROME_BIN, BROWSER_PROFILE_DIR,
    BROWSER_HEADLESS, BROWSER_TIMEOUT, SCREENSHOT_DIR
)
from logger import log_event

# ========== 自动等待配置 ==========
AUTO_WAIT_TIMEOUT_MS = 1500  # 动作执行后的强制缓冲时间（毫秒）
TAB_LOAD_TIMEOUT_MS = 3000   # 等待新标签页加载的极限时间（毫秒）

# ========== 全局单例 ==========
_pw: Optional[Playwright] = None
_context: Optional[BrowserContext] = None
_page: Optional[Page] = None

# ========== 会话失效识别 ==========
_DEAD_MARKERS = (
    "different thread",
    "which happens to have exited",
    "target page, context or browser has been closed",
    "targetclosederror",
    "profile is already in use",
)

def _is_dead_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(m in msg for m in _DEAD_MARKERS)


# ========== 会话管理 ==========
def _reset_session() -> None:
    global _pw, _context, _page
    try:
        if _context: _context.close()
    except Exception: pass
    try:
        if _pw: _pw.stop()
    except Exception: pass
    _pw = None
    _context = None
    _page = None

    # 暴力清理残留进程与锁文件
    try:
        subprocess.run(["pkill", "-f", BROWSER_PROFILE_DIR], stderr=subprocess.DEVNULL)
        time.sleep(1)
        lock_file = os.path.join(BROWSER_PROFILE_DIR, "SingletonLock")
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except Exception as e:
        log_event("warning", f"清理浏览器残留失败: {e}", stage="browser")


def _probe(page: Optional[Page]) -> bool:
    if page is None: return False
    try:
        if page.is_closed(): return False
        _ = page.url
        return True
    except Exception:
        return False


def _start_session() -> Page:
    global _pw, _context, _page
    if _pw is None:
        _pw = sync_playwright().start()

    os.makedirs(BROWSER_PROFILE_DIR, exist_ok=True)

    launch_kwargs = {
        "headless": BROWSER_HEADLESS,
        "args": ["--no-first-run", "--no-default-browser-check"],
        "viewport": {"width": 1280, "height": 900},
    }
    if CHROME_BIN:
        launch_kwargs["executable_path"] = CHROME_BIN

    try:
        _context = _pw.chromium.launch_persistent_context(BROWSER_PROFILE_DIR, **launch_kwargs)
    except Exception as e:
        _reset_session()
        raise RuntimeError(f"启动浏览器失败: {e}")

    _page = _context.pages[0] if _context.pages else _context.new_page()
    _page.set_default_timeout(BROWSER_TIMEOUT)
    return _page


def _sync_active_page() -> Optional[Page]:
    """
    智能同步最新标签页。
    如果发现新标签页，先等它加载完成，再切换控制权。
    """
    global _page
    if not _context: return None
    
    pages = _context.pages
    if not pages: return None

    # 如果发现了新标签页（通常是因为点击了 target=_blank 的链接）
    if len(pages) > 0 and pages[-1] != _page:
        latest_page = pages[-1]
        if _probe(latest_page):
            try:
                # 🚨 自动等待：等待新页面完成初步的 DOM 加载
                latest_page.wait_for_load_state("domcontentloaded", timeout=TAB_LOAD_TIMEOUT_MS)
            except Exception:
                pass # 哪怕超时也继续，总比直接报错强
            
            _page = latest_page
            _page.set_default_timeout(BROWSER_TIMEOUT)
            log_event("info", f"检测到新标签页，已自动切换: {_page.url}", stage="browser", event="browser.tab_switched")
            return _page
            
    return _page


def _get_page() -> Page:
    synced = _sync_active_page()
    if synced and _probe(synced):
        return synced

    if _probe(_page):
        return _page

    if _page is not None or _context is not None or _pw is not None:
        log_event("info", "browser session 失效，重建", stage="browser", event="browser.session.rebuild")
        _reset_session()

    return _start_session()


def _safe_call(fn: Callable, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        if not _is_dead_error(e):
            raise
        log_event("warning", f"browser session 失效，重建后重试: {e}", stage="browser", event="browser.session.dead_retry")
        _reset_session()
        return fn(*args, **kwargs)


import threading

def _reset_session_with_timeout(timeout: float = 2.0) -> None:
    done = threading.Event()
    def _do():
        _reset_session()
        done.set()
    t = threading.Thread(target=_do, daemon=True)
    t.start()
    done.wait(timeout=timeout)

def close() -> None:
    _reset_session_with_timeout(timeout=2.0)


# ========== 对外接口 ==========
def current_url() -> str:
    try: return _safe_call(lambda: _get_page().url)
    except Exception: return ""


def _navigate_impl(url: str) -> str:
    page = _get_page()
    page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT)
    # 🚨 自动等待
    page.wait_for_timeout(AUTO_WAIT_TIMEOUT_MS)
    return f"✅ 已打开: {page.url}\n标题: {page.title()}"

def navigate(url: str) -> str:
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    try: return _safe_call(_navigate_impl, url)
    except Exception as e: return f"❌ 打开失败: {e}"


def _click_impl(selector: str) -> str:
    page = _get_page()
    page.locator(selector).first.click(timeout=BROWSER_TIMEOUT)
    # 🚨 自动等待：给新标签页或 JS 事件一点触发时间
    page.wait_for_timeout(AUTO_WAIT_TIMEOUT_MS)
    return f"✅ 已点击: {selector}"

def click(selector: str) -> str:
    if not selector or not selector.strip(): return "❌ 未提供选择器"
    try: return _safe_call(_click_impl, selector)
    except Exception as e: return f"❌ 点击失败: {e}"


def _fill_impl(selector: str, value: str) -> str:
    page = _get_page()
    page.locator(selector).first.fill(value, timeout=BROWSER_TIMEOUT)
    return f"✅ 已填充 {selector}"

def fill(selector: str, value: str) -> str:
    if not selector or not selector.strip(): return "❌ 未提供选择器"
    try: return _safe_call(_fill_impl, selector, value)
    except Exception as e: return f"❌ 填写失败: {e}"


def _press_impl(key: str) -> str:
    page = _get_page()
    page.keyboard.press(key)
    # 🚨 自动等待：按下回车经常触发跳转或新标签页
    page.wait_for_timeout(AUTO_WAIT_TIMEOUT_MS)
    return f"✅ 已按键: {key}"

def press(key: str) -> str:
    if not key or not key.strip(): return "❌ 未提供按键"
    try: return _safe_call(_press_impl, key)
    except Exception as e: return f"❌ 按键失败: {e}"


def _evaluate_impl(js: str):
    page = _get_page()
    result = page.evaluate(js)
    if result is None:
        return "（JS 返回了 None）\n提示：page.evaluate 返回的是 JS 表达式的值，不是 console.log 的输出。\n要拿到数据，请用 return 或直接写表达式，不要用 console.log。\n"
    return result

def evaluate(js: str):
    if not js or not js.strip(): return "❌ 未提供 JS"
    try: return _safe_call(_evaluate_impl, js)
    except Exception as e: return f"❌ JS 异常: {e}"


def _snapshot_impl(max_chars: int) -> str:
    page = _get_page()
    title = page.title()
    url = page.url
    text = page.evaluate(f"() => (document.body ? document.body.innerText : '').slice(0, {max_chars})")
    return "\n".join([f"标题: {title}", f"URL: {url}", f"内容:", text or "(空)"])

def snapshot(max_chars: int = 1500) -> str:
    max_chars = max(500, min(max_chars, 5000))
    try: return _safe_call(_snapshot_impl, max_chars)
    except Exception as e: return f"❌ 快照失败: {e}"


def _screenshot_impl(path: str) -> str:
    page = _get_page()
    page.screenshot(path=path, full_page=False)
    return f"✅ 截图已保存: {path}"

def screenshot(path: str = None) -> str:
    if not path:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        path = os.path.join(SCREENSHOT_DIR, f"browser_{time.strftime('%Y%m%d_%H%M%S')}.png")
    try: return _safe_call(_screenshot_impl, path)
    except Exception as e: return f"❌ 截图失败: {e}"


def wait(seconds: float = 2.0) -> str:
    try:
        time.sleep(min(max(seconds, 0.5), 10))
        return f"✅ 等待 {seconds} 秒"
    except Exception as e: return f"❌ 等待失败: {e}"


def _mouse_click_impl(x: float, y: float) -> str:
    page = _get_page()
    page.mouse.click(x, y)
    page.wait_for_timeout(AUTO_WAIT_TIMEOUT_MS)
    return f"✅ 鼠标点击坐标: ({x}, {y})"

def mouse_click(x: float, y: float) -> str:
    try: return _safe_call(_mouse_click_impl, x, y)
    except Exception as e: return f"❌ 物理点击失败: {e}"