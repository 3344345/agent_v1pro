import threading
from core.sys_utils import kill_process_tree

class StopException(Exception):
    """用户按下停止按钮时抛出的异常"""
    pass


class StopToken:
    def __init__(self):
        self._stop_event = threading.Event()
        self._procs = []
        self._backends = []
        self._lock = threading.Lock()

    def stop(self):
        """触发停止信号：杀进程 + 断流"""
        self._stop_event.set()
        with self._lock:
            # 1. 强杀所有注册的子进程
            for p in self._procs:
                self._kill_proc(p)
            self._procs.clear()
            
            # 2. 中断所有注册的 LLM 后端（断开 HTTP 请求）
            for b in self._backends:
                try:
                    if hasattr(b, "abort_current"):
                        b.abort_current()
                except Exception:
                    pass
            self._backends.clear()

    def is_stopped(self):
        return self._stop_event.is_set()

    def check(self):
        """在循环中检查是否停止，如果停止则抛出异常"""
        if self.is_stopped():
            raise StopException("用户按下停止按钮")

    def register_proc(self, proc):
        with self._lock:
            self._procs.append(proc)

    def unregister_proc(self, proc):
        with self._lock:
            if proc in self._procs:
                self._procs.remove(proc)

    def register_backend(self, backend):
        with self._lock:
            self._backends.append(backend)

    def unregister_backend(self, backend):
        with self._lock:
            if backend in self._backends:
                self._backends.remove(backend)

    def _kill_proc(self, proc):
        if proc is None or proc.poll() is not None:
            return
        try:
            # 调用跨平台的进程组强杀
            kill_process_tree(proc)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


# ======================================================
# 全局线程级令牌管理（确保多线程下互不干扰）
# ======================================================
_thread_local = threading.local()

def set_current(token: StopToken):
    """为当前线程设置 StopToken"""
    _thread_local.token = token

def get_current() -> StopToken:
    """获取当前线程的 StopToken"""
    return getattr(_thread_local, "token", None)