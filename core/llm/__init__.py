"""
LLM 后端统一入口 + 空响应兜底。

- planner 后端：config.LLM_BACKEND
- router 后端：config.ROUTER_BACKEND（当前固定 llamacpp_server on CPU）
"""

from typing import Optional

from config import (
    LLM_BACKEND, ROUTER_BACKEND,
    ROUTER_MODEL, ROUTER_OPTIONS,
    PLANNER_MODEL, PLANNER_OPTIONS,
)
from core.llm.base import LLMBackend
from logger import log_event


# ========== 后端工厂 ==========
_backend: Optional[LLMBackend] = None
_router_backend: Optional[LLMBackend] = None


def make_backend(name: str = None, profile: str = "planner") -> LLMBackend:
    """按名字创建后端实例"""
    name = name or LLM_BACKEND

    if name == "ollama":
        from core.llm.ollama import OllamaBackend
        return OllamaBackend()

    elif name == "llamacpp_server":
        from core.llm.llamacpp_server import LlamaCppServerBackend
        return LlamaCppServerBackend(profile=profile)

    elif name == "llamacpp_direct":
        from core.llm.llamacpp_direct import LlamaCppDirectBackend
        return LlamaCppDirectBackend()

    elif name == "cloud_api":
        from core.llm.cloud_api import CloudApiBackend
        return CloudApiBackend(profile=profile)

    elif name == "freetoken":
        raise NotImplementedError("FreeToken 后端尚未实现")

    else:
        raise ValueError(f"未知后端: {name!r}")


def get_backend() -> LLMBackend:
    """planner 后端单例"""
    global _backend
    if _backend is None:
        _backend = make_backend(LLM_BACKEND, profile="planner")
    return _backend


def get_router_backend() -> LLMBackend:
    """router 后端单例（CPU 1.5B）"""
    global _router_backend
    if _router_backend is None:
        _router_backend = make_backend(ROUTER_BACKEND, profile="router")
    return _router_backend


def reset_backend() -> None:
    """关闭并清空两个后端"""
    global _backend, _router_backend
    for b in (_backend, _router_backend):
        if b is not None:
            try:
                b.close()
            except Exception:
                pass
    _backend = None
    _router_backend = None


def switch_backend(name: str) -> LLMBackend:
    """运行时切换 planner 后端"""
    global _backend
    if _backend is not None:
        try:
            _backend.close()
        except Exception:
            pass
    _backend = make_backend(name, profile="planner")
    return _backend


# ========== 空响应判定 ==========
def _is_empty_response(result: dict):
    if not isinstance(result, dict) or "error" in result:
        return False, None, {}

    msg = result.get("message", {}) or {}
    content = (msg.get("content") or "").strip()
    has_tools = bool(msg.get("tool_calls"))

    meta = {
        "content_len": len(content),
        "has_tools": has_tools,
        "done_reason": result.get("done_reason"),
        "eval_count": result.get("eval_count"),
        "prompt_eval_count": result.get("prompt_eval_count"),
    }

    if content: return False, None, meta
    if has_tools: return False, None, meta
    if (msg.get("thinking") or "").strip(): return True, "thinking_only", meta
    return True, "empty", meta


# ========== 上层统一入口 ==========
def call_planner(messages, tools=None, retry=True, log_fn=None):
    def _log(level, msg, extra=None):
        if log_fn:
            log_fn(level, msg, stage="llm", extra=extra)
        else:
            log_event(level, msg, stage="llm", extra=extra)

    backend = get_backend()

    result = backend.chat(PLANNER_MODEL, messages, tools, PLANNER_OPTIONS)
    if "error" in result:
        return result

    is_empty, reason, meta = _is_empty_response(result)
    if not is_empty:
        return result

    _log("warning", "模型空响应", {"attempt": 1, "reason": reason, **meta})
    if not retry:
        return {"error": "模型空响应", "stage": "empty_response", "meta": meta}

    retry_messages = list(messages) + [{"role": "user", "content": "请用简洁的中文总结当前进展。不要再调用工具。"}]
    _log("info", f"空响应重试：追加总结提示（保留 {len(messages)} 条上下文）")
    result = backend.chat(PLANNER_MODEL, retry_messages, tools=None, options=PLANNER_OPTIONS)
    
    if "error" in result: return result
    is_empty, reason, meta = _is_empty_response(result)
    if not is_empty: return result

    _log("warning", "模型空响应", {"attempt": 2, "reason": reason, **meta})

    retry_messages.append({"role": "user", "content": "请直接输出文字总结，不要再调用工具，也不要返回空内容。"})
    _log("info", "空响应重试：强制要求文字输出")
    result = backend.chat(PLANNER_MODEL, retry_messages, tools=None, options=PLANNER_OPTIONS)
    
    if "error" in result: return result
    is_empty, reason, meta = _is_empty_response(result)
    if not is_empty: return result

    _log("error", "模型连续三次空响应", {"attempt": 3, "reason": reason, **meta})
    return {"error": "模型连续空响应", "stage": "empty_response", "meta": meta}


def call_router(messages):
    return get_router_backend().chat(ROUTER_MODEL, messages, options=ROUTER_OPTIONS)


def call_validator(messages):
    return get_router_backend().chat(ROUTER_MODEL, messages, options=ROUTER_OPTIONS)