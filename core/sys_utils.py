import os
import sys
import signal
import subprocess

IS_WINDOWS = sys.platform.startswith("win")

def start_process(cmd, **kwargs):
    """跨平台启动子进程（自动处理进程组）"""
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["preexec_fn"] = os.setsid
    return subprocess.Popen(cmd, **kwargs)

def kill_process_tree(proc):
    """跨平台强杀整个进程树"""
    if proc is None or proc.poll() is not None:
        return
    try:
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass