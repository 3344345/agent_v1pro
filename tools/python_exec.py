import os
import sys
import tempfile
import subprocess
import re
from registries.tool_registry import register
from runtime.stop_token import get_current, StopException
from core.sys_utils import start_process, kill_process_tree
from config import MPL_FONT_FAMILY

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MPL_HEADER = f"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['{MPL_FONT_FAMILY}', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
"""

_HIDDEN_ERROR_MARKERS = ("Traceback (most recent call last)", "Error:", "Exception:")

@register(
    name="execute_python",
    description="执行 Python 代码片段，返回 stdout / stderr。用于计算、数据处理、绘制图表、调用 Python 库。",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "要执行的 Python 代码"},
            "timeout": {"type": "integer", "description": "超时秒数，默认 60"},
        },
        "required": ["code"],
    },
    requires_network=False,
)
def execute_python(code: str, timeout: int = 60) -> str:
    if not code or not code.strip(): return "❌ 未提供代码"

    dangerous_patterns = [r"os\.system", r"subprocess\.", r"shutil\.rmtree", r"os\.remove", r"os\.unlink", r"eval\(", r"exec\("]
    for pat in dangerous_patterns:
        if re.search(pat, code):
            return f"❌ 拒绝执行：代码包含高危操作（{pat}）。请使用 execute_command 并在用户确认下执行。"

    full_code = MPL_HEADER + "\n" + code if ("matplotlib" in code or "plt." in code) else code

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(full_code)
        script_path = f.name

    python_bin = sys.executable
    token = get_current()

    try:
        proc = start_process([python_bin, script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=PROJECT_ROOT)
    except Exception as e:
        try: os.unlink(script_path)
        except Exception: pass
        return f"❌ 启动失败: {e}"

    if token is not None: token.register_proc(proc)

    stdout, stderr, timed_out = "", "", False
    try:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as e:
            timed_out = True
            kill_process_tree(proc)
            out_part = e.stdout.decode("utf-8", errors="ignore") if isinstance(e.stdout, bytes) else (e.stdout or "")
            err_part = e.stderr.decode("utf-8", errors="ignore") if isinstance(e.stderr, bytes) else (e.stderr or "")
            if not out_part and not err_part:
                try:
                    _out, _err = proc.communicate(timeout=1)
                    out_part, err_part = _out or "", _err or ""
                except Exception: pass
            stdout, stderr = out_part, err_part
            try: proc.wait(timeout=2)
            except Exception: pass
    finally:
        if token is not None: token.unregister_proc(proc)
        try: os.unlink(script_path)
        except Exception: pass

    if token is not None and token.is_stopped(): raise StopException("用户按下停止按钮")

    if timed_out:
        stderr = (stderr or "") + f"\n[系统强制终止] 执行超时（{timeout} 秒）"
        returncode = -9
    else:
        returncode = proc.returncode

    combined = (stdout or "") + "\n" + (stderr or "")
    has_hidden_error = any(m in combined for m in _HIDDEN_ERROR_MARKERS)

    parts = []
    if returncode == 0 and has_hidden_error:
        parts.append("⚠️ 执行完成，但输出里检测到错误信息（退出码 0）。注意：脚本可能自己 try/except 了异常。")
    elif returncode == 0: parts.append("✅ 执行成功（退出码 0）")
    else: parts.append(f"❌ 执行失败（退出码 {returncode}）")

    if stdout: parts.append(f"\n[stdout]\n{stdout[:3000]}")
    if stderr:
        s = stderr
        if "findfont" in s and "Font family" in s:
            s = "\n".join(line for line in s.split("\n") if "findfont" not in line and "Font family" not in line)
        if s.strip(): parts.append(f"\n[stderr]\n{s[:2000]}")

    return "\n".join(parts)