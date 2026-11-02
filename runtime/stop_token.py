"""
StopToken：直接停止

- 机械停止，不走 LLM 决策
- 5 秒内完成
- 子进程 killpg，LLM 请求 abort

线程安全：stop() 从主线程调用，register/check 从工作线程调用。
"""

import os
import signal
import threading
from typing import List, Optional


class StopException(Exception):
    """run_agent 检测到停止信号时抛出"""
    pass


# ========== 全局当前 token（供 executor 用） ==========
_current: Optional["StopToken"] = None


def set_current(token: Optional["StopToken"]) -> None:
    global _current
    _current = token


def get_current() -> Optional["StopToken"]:
    return _current


# ========== 主体 ==========
class StopToken:
    def __init__(self):
        self._stopped = False
        self._lock = threading.Lock()
        self._procs: List = []          # 子进程 Popen 对象
        self._backends: List = []       # 有 abort_current 方法的 backend

    # ---------- 注册 ----------
    def register_proc(self, proc) -> None:
        """注册子进程。已停止则立刻 kill。"""
        with self._lock:
            if self._stopped:
                self._kill_proc(proc)
                return
            self._procs.append(proc)

    def unregister_proc(self, proc) -> None:
        with self._lock:
            try:
                self._procs.remove(proc)
            except ValueError:
                pass

    def register_backend(self, backend) -> None:
        """注册后端。已停止则立刻 abort。"""
        with self._lock:
            if self._stopped:
                self._abort_backend(backend)
                return
            self._backends.append(backend)

    def unregister_backend(self, backend) -> None:
        with self._lock:
            try:
                self._backends.remove(backend)
            except ValueError:
                pass

    # ---------- 查询 ----------
    def is_stopped(self) -> bool:
        with self._lock:
            return self._stopped

    def check(self) -> None:
        """工作线程周期性调用。已停止则抛 StopException。"""
        if self.is_stopped():
            raise StopException("用户按下停止按钮")

    # ---------- 触发 ----------
    def stop(self) -> None:
        """机械执行，< 5s。"""
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            procs = list(self._procs)
            backends = list(self._backends)

        # 1) kill 所有子进程（killpg 一锅端）
        for proc in procs:
            self._kill_proc(proc)

        # 2) abort 所有 backend（关 session 让阻塞的请求立刻抛异常）
        for backend in backends:
            self._abort_backend(backend)

    # ---------- 内部 ----------
    def _kill_proc(self, proc) -> None:
        if proc is None or proc.poll() is not None:
            return
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except Exception:
                pass

    def _abort_backend(self, backend) -> None:
        try:
            backend.abort_current()
        except Exception:
            pass