import time
import logging
import subprocess
import platform
import requests

from config import OLLAMA_URL, TIMEOUT
from core.llm.base import LLMBackend
from logger import log_event

logger = logging.getLogger("agent.llm.ollama")

class OllamaBackend(LLMBackend):
    """Ollama 后端（HTTP API）"""

    SUPPORTED = {"interrupt"}

    def __init__(self, base_url: str = OLLAMA_URL):
        self.base_url = base_url
        self._session = requests.Session()

    def _ensure_alive(self) -> bool:
        """探活：如果 Ollama 守护进程挂了，尝试在后台物理重启它"""
        if self.is_available():
            return True
            
        log_event("warning", "Ollama 服务失联或无响应，尝试进行物理重启...", stage="llm")
        try:
            if platform.system() == "Darwin": # macOS 专属
                # 1. 暴力杀掉可能因休眠卡死 Metal 上下文的僵尸进程
                subprocess.run(["killall", "Ollama"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                time.sleep(1) 
                # 2. 重新拉起应用（会重新初始化 GPU）
                subprocess.Popen(["open", "-a", "Ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else: # Linux/Windows
                subprocess.run(["pkill", "-f", "ollama serve"], stderr=subprocess.DEVNULL)
                time.sleep(1)
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            # 等待最多 15 秒，看服务是否起来
            for _ in range(15):
                time.sleep(1)
                if self.is_available():
                    log_event("info", "Ollama 服务已成功自动重启", stage="llm")
                    return True
            return False
        except Exception as e:
            log_event("error", f"自动拉起 Ollama 失败: {e}", stage="llm")
            return False

    def chat(self, model, messages, tools=None, options=None, timeout=None) -> dict:
        if not self._ensure_alive():
            return {"error": "Ollama 服务不可用，且自动重启失败"}

        opts = dict(options or {})
        think = opts.pop("think", None)

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": opts,
        }
        if think is not None:
            payload["think"] = think
        if tools:
            payload["tools"] = tools

        log_event(
            "debug", "llm call", stage="llm", event="llm.call",
            extra={"backend": "ollama", "model": model,
                   "messages": len(messages), "tools": len(tools or [])},
        )

        t0 = time.monotonic()
        try:
            resp = self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=timeout or TIMEOUT,
            )
            resp.raise_for_status()
            result = resp.json()
            elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

            msg = result.get("message") or {}
            tool_calls = msg.get("tool_calls") or []

            log_event(
                "debug", "llm done", stage="llm", event="llm.done",
                extra={
                    "backend": "ollama",
                    "model": model,
                    "done_reason": result.get("done_reason"),
                    "eval_count": result.get("eval_count"),
                    "prompt_eval_count": result.get("prompt_eval_count"),
                    "tool_calls": len(tool_calls),
                    "elapsed_ms": elapsed_ms,
                },
            )
            return result
        except Exception as e:
            elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
            log_event(
                "error", "llm error", stage="llm", event="llm.error",
                extra={"backend": "ollama", "model": model,
                       "error": str(e), "elapsed_ms": elapsed_ms},
            )
            return {"error": str(e)}

    def embed(self, model, texts):
        if not self._ensure_alive():
            return []
            
        try:
            resp = self._session.post(
                f"{self.base_url}/api/embed",
                json={"model": model, "input": texts},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json().get("embeddings", [])
        except Exception as e:
            log_event("warning", "embed failed", stage="llm", event="llm.error",
                      extra={"backend": "ollama", "model": model, "error": str(e)})
            return []

    def is_available(self) -> bool:
        try:
            resp = self._session.get(f"{self.base_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False
        
    def abort_current(self) -> None:
        log_event("info", "中断当前 LLM 请求", stage="llm", event="llm.abort",
                  extra={"backend": "ollama"})
        try:
            self._session.close()
        except Exception:
            pass
        self._session = requests.Session()

    def close(self) -> None:
        self._session.close()