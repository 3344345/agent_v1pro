"""
llama.cpp server 后端（支持 planner / router 两种 profile）。

planner: 9B on GPU，端口 8081
router:  1.5B on CPU，端口 8082

suspend 兼容：
- systemd sleep hook 会在 suspend 前 kill server
- 本后端每次 chat/embed 前 ping /health，失联则自动重启
- _ensure_server 启动后校验是否真的跑在 GPU（防止静默降级 CPU）
"""

import os
import time
import signal
import subprocess
from typing import Optional

import requests

from config import (
    # planner
    LLAMACPP_BIN, LLAMACPP_MODEL, LLAMACPP_URL,
    LLAMACPP_HOST, LLAMACPP_PORT, LLAMACPP_CTX,
    LLAMACPP_NGL, LLAMACPP_PARALLEL,
    LLAMACPP_REASONING, LLAMACPP_REASONING_BUDGET,
    LLAMACPP_CHAT_TEMPLATE_KWARGS,
    LLAMACPP_KV_QUANT, LLAMACPP_TIMEOUT,
    # router
    ROUTER_SERVER_BIN, ROUTER_SERVER_MODEL, ROUTER_SERVER_URL,
    ROUTER_SERVER_HOST, ROUTER_SERVER_PORT, ROUTER_SERVER_CTX,
    ROUTER_SERVER_NGL, ROUTER_SERVER_PARALLEL,
    ROUTER_SERVER_REASONING, ROUTER_SERVER_REASONING_BUDGET,
    ROUTER_SERVER_CHAT_TEMPLATE_KWARGS,
    ROUTER_SERVER_TIMEOUT,
    # 通用
    LOG_DIR,
)
from core.llm.base import LLMBackend
from core.sys_utils import start_process, kill_process_tree  # <--- 引入解耦工具
from logger import log_event


class LlamaCppServerBackend(LLMBackend):
    SUPPORTED = {"save_state", "load_state", "interrupt"}

    def __init__(self, profile: str = "planner", auto_start: bool = True,
                 model: Optional[str] = None):
        self.profile = profile

        if profile == "planner":
            self.bin      = LLAMACPP_BIN
            self.model_path = model or LLAMACPP_MODEL
            self.base_url = LLAMACPP_URL
            self.host     = LLAMACPP_HOST
            self.port     = LLAMACPP_PORT
            self.ctx      = LLAMACPP_CTX
            self.ngl      = LLAMACPP_NGL
            self.parallel = LLAMACPP_PARALLEL
            self.reasoning = LLAMACPP_REASONING
            self.reasoning_budget = LLAMACPP_REASONING_BUDGET
            self.chat_template_kwargs = LLAMACPP_CHAT_TEMPLATE_KWARGS
            self.kv_quant = LLAMACPP_KV_QUANT
            self.timeout  = LLAMACPP_TIMEOUT
            self.log_name = "llama-server-planner.log"
        elif profile == "router":
            self.bin      = ROUTER_SERVER_BIN
            self.model_path = model or ROUTER_SERVER_MODEL
            self.base_url = ROUTER_SERVER_URL
            self.host     = ROUTER_SERVER_HOST
            self.port     = ROUTER_SERVER_PORT
            self.ctx      = ROUTER_SERVER_CTX
            self.ngl      = ROUTER_SERVER_NGL
            self.parallel = ROUTER_SERVER_PARALLEL
            self.reasoning = ROUTER_SERVER_REASONING
            self.reasoning_budget = ROUTER_SERVER_REASONING_BUDGET
            self.chat_template_kwargs = ROUTER_SERVER_CHAT_TEMPLATE_KWARGS
            self.kv_quant = False
            self.timeout  = ROUTER_SERVER_TIMEOUT
            self.log_name = "llama-server-router.log"
        else:
            raise ValueError(f"未知 profile: {profile!r}")

        self._session = requests.Session()
        self._proc: Optional[subprocess.Popen] = None
        self._server_log = None
        self._log_offset = 0           # 本次启动的日志起点
        if auto_start:
            self._ensure_server()

    # ---------- 服务生命周期 ----------
    def _build_cmd(self):
        cmd = [
            self.bin,
            "-m", self.model_path,
            "--host", self.host,
            "--port", str(self.port),
            "-c", str(self.ctx),
            "-ngl", str(self.ngl),
            "-np", str(self.parallel),
            "--jinja",
            "--reasoning", self.reasoning,
            "--reasoning-budget", str(self.reasoning_budget),
            "--chat-template-kwargs", self.chat_template_kwargs,
        ]
        if self.kv_quant:
            cmd += ["--cache-type-k", "q8_0", "--cache-type-v", "q8_0"]
        return cmd

    def _ensure_server(self):
        if self.is_available():
            log_event("info", f"[{self.profile}] llama-server 已运行，复用",
                      stage="llm", event="llm.server.reuse",
                      extra={"profile": self.profile})
            return

        cmd = self._build_cmd()
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, self.log_name)
        # 记录本次启动前的日志大小，_verify_gpu 只看之后的内容
        try:
            self._log_offset = os.path.getsize(log_path)
        except OSError:
            self._log_offset = 0
        self._server_log = open(log_path, "a", encoding="utf-8")

        log_event("info", f"[{self.profile}] 启动 llama-server", stage="llm",
                  event="llm.server.start",
                  extra={"profile": self.profile,
                         "cmd": " ".join(cmd), "log": log_path})

        # ================= 解耦核心：使用 start_process =================
        self._proc = start_process(
            cmd,
            stdout=self._server_log,
            stderr=self._server_log,
        )
        # ==============================================================
        
        self._wait_ready()

    def _wait_ready(self, timeout: int = 180):
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout:
            if self._proc and self._proc.poll() is not None:
                raise RuntimeError(
                    f"[{self.profile}] llama-server 启动即退出，"
                    f"查看 {LOG_DIR}/{self.log_name}"
                )
            if self.is_available():
                elapsed = round((time.monotonic() - t0) * 1000, 1)
                log_event("info", f"[{self.profile}] llama-server 就绪", stage="llm",
                          event="llm.server.ready",
                          extra={"profile": self.profile, "elapsed_ms": elapsed})
                # 就绪后校验 GPU
                self._verify_gpu()
                return
            time.sleep(0.5)
        raise TimeoutError(f"[{self.profile}] llama-server {timeout}s 内未就绪")

    def _verify_gpu(self):
        """检查 server 是否真的跑在 GPU 上。降级则报警。

        - ngl == 0 的 profile（router）本身就是 CPU，跳过校验
        - 只看本次启动之后写入的日志内容（用 _log_offset 定位）
        """
        # router 本身就是 CPU，不校验
        if self.ngl == 0:
            return

        log_path = os.path.join(LOG_DIR, self.log_name)
        if not os.path.exists(log_path):
            return
        try:
            with open(log_path, "rb") as f:
                f.seek(self._log_offset)
                raw = f.read()
            content = raw.decode("utf-8", errors="ignore")
        except Exception:
            return

        degraded_markers = [
            "no usable GPU found",
            "failed to initialize CUDA",
            "offloaded 0/",
        ]
        hit = next((m for m in degraded_markers if m in content), None)
        if hit:
            msg = f"[{self.profile}] llama-server 跑在 CPU 上（{hit}）"
            log_event("error", msg, stage="llm", event="llm.server.degraded",
                      extra={"profile": self.profile, "marker": hit})
            print(f"\n⚠️  {msg}")
            print(f"    查看 {log_path}")
            print(f"    可能原因：CUDA sticky error（需重启系统）或显存不足\n")
        else:
            log_event("debug", f"[{self.profile}] GPU 校验通过", stage="llm",
                      event="llm.server.gpu_ok",
                      extra={"profile": self.profile})

    def _shutdown(self):
        if self._proc and self._proc.poll() is None:
            log_event("info", f"[{self.profile}] 停止 llama-server", stage="llm",
                      event="llm.server.stop",
                      extra={"profile": self.profile})
            
            # ================= 解耦核心：使用 kill_process_tree =================
            kill_process_tree(self._proc)
            # ===================================================================
            
            try:
                self._proc.wait(timeout=10)
            except Exception:
                pass
        self._proc = None
        if self._server_log:
            try:
                self._server_log.close()
            except Exception:
                pass
            self._server_log = None

    # ---------- 健康探测（每次调用前） ----------
    def _ensure_alive(self) -> bool:
        """server 失联则尝试重启。返回 True 表示可用。"""
        if self.is_available():
            return True

        log_event("info", f"[{self.profile}] llama-server 失联，尝试自动重启",
                  stage="llm", event="llm.server.lost",
                  extra={"profile": self.profile})
        try:
            self._ensure_server()
            return True
        except Exception as e:
            log_event("error", f"[{self.profile}] llama-server 重启失败: {e}",
                      stage="llm", event="llm.server.restart_failed",
                      extra={"profile": self.profile, "error": str(e)})
            return False

    # ---------- 核心接口 ----------
    def chat(self, model, messages, tools=None, options=None, timeout=None) -> dict:
        # ========== 健康探测：失联则重启 ==========
        if not self._ensure_alive():
            return {"error": f"[{self.profile}] llama-server 不可用"}

        opts = dict(options or {})
        opts.pop("think", None)
        opts.pop("num_ctx", None)

        payload = {
            "model": model or "local",
            "messages": messages,
            "stream": False,
        }
        if "temperature" in opts:
            payload["temperature"] = opts["temperature"]
        if "top_p" in opts:
            payload["top_p"] = opts["top_p"]
        if "num_predict" in opts:
            payload["max_tokens"] = opts["num_predict"]
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        log_event("debug", "llm call", stage="llm", event="llm.call",
                  extra={"backend": "llamacpp_server",
                         "profile": self.profile,
                         "model": model,
                         "messages": len(messages),
                         "tools": len(tools or [])})

        t0 = time.monotonic()
        try:
            resp = self._session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=timeout or self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            elapsed_ms = round((time.monotonic() - t0) * 1000, 1)

            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            tool_calls = msg.get("tool_calls") or []
            usage = data.get("usage") or {}

            result = {
                "message": {
                    "content": msg.get("content") or "",
                    "tool_calls": tool_calls,
                },
                "done_reason": choice.get("finish_reason"),
                "eval_count": usage.get("completion_tokens"),
                "prompt_eval_count": usage.get("prompt_tokens"),
            }

            log_event("debug", "llm done", stage="llm", event="llm.done",
                      extra={
                          "backend": "llamacpp_server",
                          "profile": self.profile,
                          "model": model,
                          "done_reason": result["done_reason"],
                          "eval_count": result["eval_count"],
                          "prompt_eval_count": result["prompt_eval_count"],
                          "tool_calls": len(tool_calls),
                          "elapsed_ms": elapsed_ms,
                      })
            return result
        except Exception as e:
            elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
            log_event("error", "llm error", stage="llm", event="llm.error",
                      extra={"backend": "llamacpp_server",
                             "profile": self.profile,
                             "model": model,
                             "error": str(e),
                             "elapsed_ms": elapsed_ms})
            return {"error": str(e)}

    def embed(self, model, texts):
        # ========== 健康探测 ==========
        if not self._ensure_alive():
            return []

        try:
            resp = self._session.post(
                f"{self.base_url}/v1/embeddings",
                json={"model": model or "local", "input": texts},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data.get("data", [])]
        except Exception as e:
            log_event("warning", "embed failed", stage="llm", event="llm.error",
                      extra={"backend": "llamacpp_server",
                             "profile": self.profile,
                             "error": str(e)})
            return []

    def is_available(self) -> bool:
        try:
            resp = self._session.get(f"{self.base_url}/health", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def abort_current(self) -> None:
        """关闭 session，让正在进行的 requests.post 立刻抛异常。"""
        log_event("info", "中断当前 LLM 请求", stage="llm", event="llm.abort",
                  extra={"backend": "llamacpp_server", "profile": self.profile})
        try:
            self._session.close()
        except Exception:
            pass
        self._session = requests.Session()

    # ---------- 扩展：KV 快照 ----------
    def save_state(self, path: str) -> None:
        resp = self._session.post(
            f"{self.base_url}/slots/0/save",
            json={"filename": path},
            timeout=30,
        )
        resp.raise_for_status()

    def load_state(self, path: str) -> None:
        resp = self._session.post(
            f"{self.base_url}/slots/0/restore",
            json={"filename": path},
            timeout=30,
        )
        resp.raise_for_status()

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:
            pass
        self._shutdown()