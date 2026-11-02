"""
browser 工具后端。Playwright + Chromium。

会话自愈：
- 每次操作前探针 page 是否健康，不健康则重建
- 操作中如果遇到"session dead"错误，自动重建并重试一次

外部依赖：
- 系统 Chromium 或 Playwright 自带 chromium（`playwright install chromium`）
"""

import os
import time
from typing import Optional, Callable

from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright

from config import (
    CHROME_BIN, BROWSER_PROFILE_DIR,
    BROWSER_HEADLESS, BROWSER_TIMEOUT,
)
from logger import log_event


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
)


def _is_dead_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(m in msg for m in _DEAD_MARKERS)


# ========== 会话管理 ==========
def _reset_session() -> None:
    """彻底清理当前会话，准备重建。忽略一切异常。"""
    global _pw, _context, _page
    try:
        if _context:
            _context.close()
    except Exception:
        pass
    try:
        if _pw:
            _pw.stop()
    except Exception:
        pass
    _pw = None
    _context = None
    _page = None


def _probe(page: Optional[Page]) -> bool:
    """轻量探针：确认 page 对象还能在当前线程访问。"""
    if page is None:
        return False
    try:
        if page.is_closed():
            return False
        _ = page.url          # 纯本地属性访问，零成本
        return True
    except Exception:
        return False


def _start_session() -> Page:
    """启动一个新的 browser session，返回可用 page。"""
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
        _context = _pw.chromium.launch_persistent_context(
            BROWSER_PROFILE_DIR, **launch_kwargs
        )
    except Exception as e:
        _reset_session()
        raise RuntimeError(f"启动浏览器失败: {e}")

    _page = _context.pages[0] if _context.pages else _context.new_page()
    _page.set_default_timeout(BROWSER_TIMEOUT)
    return _page


def _get_page() -> Page:
    """获取可用的 page。现有会话失效时自动重建。"""
    if _probe(_page):
        return _page

    # 探针失败：清理并重建
    if _page is not None or _context is not None or _pw is not None:
        log_event("info", "browser session 失效，重建",
                  stage="browser", event="browser.session.rebuild")
        _reset_session()

    return _start_session()


def _safe_call(fn: Callable, *args, **kwargs):
    """执行依赖 browser 的操作。

    遇到"session dead"类错误时自动重建并重试一次。
    其他异常原样抛出。
    """
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        if not _is_dead_error(e):
            raise
        log_event("warning", f"browser session 失效，重建后重试: {e}",
                  stage="browser", event="browser.session.dead_retry",
                  extra={"error": str(e)})
        _reset_session()
        return fn(*args, **kwargs)


import threading

def _reset_session_with_timeout(timeout: float = 2.0) -> None:
    """带超时的重置。超时放弃，不阻塞。"""
    done = threading.Event()

    def _do():
        _reset_session()
        done.set()

    t = threading.Thread(target=_do, daemon=True)
    t.start()
    done.wait(timeout=timeout)


def close() -> None:
    """关闭浏览器和 Playwright 驱动（带 2 秒超时）。"""
    _reset_session_with_timeout(timeout=2.0)


# ========== 对外接口 ==========
def _current_url_impl() -> str:
    return _get_page().url


def current_url() -> str:
    try:
        return _safe_call(_current_url_impl)
    except Exception:
        return ""


def _navigate_impl(url: str) -> str:
    page = _get_page()
    page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_TIMEOUT)
    return f"✅ 已打开: {page.url}\n标题: {page.title()}"


def navigate(url: str) -> str:
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    try:
        return _safe_call(_navigate_impl, url)
    except Exception as e:
        return f"❌ 打开失败: {e}"


def _click_impl(selector: str) -> str:
    page = _get_page()
    page.click(selector, timeout=BROWSER_TIMEOUT)
    return f"✅ 已点击: {selector}"


def click(selector: str) -> str:
    if not selector or not selector.strip():
        return "❌ 未提供选择器"
    try:
        return _safe_call(_click_impl, selector)
    except Exception as e:
        return f"❌ 点击失败: {e}"


def _fill_impl(selector: str, value: str) -> str:
    page = _get_page()
    page.fill(selector, value, timeout=BROWSER_TIMEOUT)
    return f"✅ 已填充 {selector}"


def fill(selector: str, value: str) -> str:
    if not selector or not selector.strip():
        return "❌ 未提供选择器"
    try:
        return _safe_call(_fill_impl, selector, value)
    except Exception as e:
        return f"❌ 填写失败: {e}"


def _press_impl(key: str) -> str:
    page = _get_page()
    page.keyboard.press(key)
    return f"✅ 已按键: {key}"


def press(key: str) -> str:
    if not key or not key.strip():
        return "❌ 未提供按键"
    try:
        return _safe_call(_press_impl, key)
    except Exception as e:
        return f"❌ 按键失败: {e}"


def _evaluate_impl(js: str):
    page = _get_page()
    result = page.evaluate(js)
    if result is None:
        return (
            "（JS 返回了 None）\n"
            "提示：page.evaluate 返回的是 JS 表达式的值，不是 console.log 的输出。\n"
            "要拿到数据，请用 return 或直接写表达式，不要用 console.log。\n"
            "例：把 `console.log(x)` 改成 `return x`；\n"
            "    把 `let a=...; let b=...; console.log(a,b)` 改成 "
            "`() => { let a=...; let b=...; return [a,b]; }`。"
        )
    return result


def evaluate(js: str):
    if not js or not js.strip():
        return "❌ 未提供 JS"
    try:
        return _safe_call(_evaluate_impl, js)
    except Exception as e:
        return f"❌ JS 异常: {e}"


def _snapshot_impl(max_chars: int) -> str:
    page = _get_page()
    title = page.title()
    url = page.url
    text = page.evaluate(
        f"() => (document.body ? document.body.innerText : '').slice(0, {max_chars})"
    )
    return "\n".join([
        f"标题: {title}",
        f"URL: {url}",
        f"内容:",
        text or "(空)",
    ])


def snapshot(max_chars: int = 1500) -> str:
    # 硬顶 5000，防止上下文被长文档淹没
    max_chars = max(500, min(max_chars, 5000))
    try:
        return _safe_call(_snapshot_impl, max_chars)
    except Exception as e:
        return f"❌ 快照失败: {e}"


def _screenshot_impl(path: str) -> str:
    page = _get_page()
    page.screenshot(path=path, full_page=False)
    return f"✅ 截图已保存: {path}"


def screenshot(path: str = None) -> str:
    if not path:
        from config import SCREENSHOT_DIR
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        path = os.path.join(
            SCREENSHOT_DIR,
            f"browser_{time.strftime('%Y%m%d_%H%M%S')}.png"
        )
    try:
        return _safe_call(_screenshot_impl, path)
    except Exception as e:
        return f"❌ 截图失败: {e}"


def wait(seconds: float = 2.0) -> str:
    try:
        time.sleep(min(max(seconds, 0.5), 10))
        return f"✅ 等待 {seconds} 秒"
    except Exception as e:
        return f"❌ 等待失败: {e}"