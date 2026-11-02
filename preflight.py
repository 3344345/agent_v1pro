"""
启动前 / server 重启前的依赖检查。

两种范围：
- scope="full"   : Agent 启动时全套检查
- scope="server" : llama-server 重启前检查（更轻量）

返回 (ok, issues)：
- ok=True 表示无 fatal
- issues 是 [(level, name, message), ...]
  level = "fatal" | "warning"
"""

import os
import re
import shutil
import signal
import subprocess
from typing import List, Optional, Tuple

from config import (
    LLM_BACKEND,  # <--- 新增：引入当前后端标识
    LLAMACPP_BIN, LLAMACPP_MODEL, LLAMACPP_PORT,
    ROUTER_SERVER_MODEL, ROUTER_SERVER_PORT,
    CHROME_BIN, DATA_DIR,
)
from logger import log_event


Issue = Tuple[str, str, str]   # (level, name, message)


# ========== 单项检查 ==========
def _check_gpu() -> Optional[Issue]:
    """用 llama-cli --list-devices 探测 CUDA。"""
    llama_cli = os.path.join(os.path.dirname(LLAMACPP_BIN), "llama-cli")
    if not os.path.exists(llama_cli):
        return ("warning", "GPU", f"找不到 {llama_cli}，跳过 GPU 检查")

    try:
        result = subprocess.run(
            [llama_cli, "--list-devices"],
            capture_output=True, text=True, timeout=15,
        )
        out = (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired:
        return ("fatal", "GPU", "llama-cli --list-devices 超时")
    except Exception as e:
        return ("fatal", "GPU", f"探测失败: {e}")

    if "CUDA0" in out:
        return None
    if "failed to initialize CUDA" in out:
        return ("fatal", "GPU",
                "CUDA 初始化失败（sticky error 状态），需要重启系统")
    if "no CUDA devices" in out.lower():
        return ("fatal", "GPU", "未检测到 CUDA 设备")
    return ("fatal", "GPU", f"未识别 GPU 可用性：{out[:200]}")


def _check_file(path: str, name: str, min_gb: float = 0.1) -> Optional[Issue]:
    if not path:
        return None
    if not os.path.exists(path):
        return ("fatal", name, f"文件不存在: {path}")
    size_gb = os.path.getsize(path) / (1024 ** 3)
    if size_gb < min_gb:
        return ("fatal", name, f"文件异常小 ({size_gb:.2f}GB): {path}")
    return None


def _check_port_occupied(port: int) -> Optional[dict]:
    """返回 None 表示端口空闲；否则返回 {"pid": int, "comm": str}。"""
    try:
        out = subprocess.check_output(
            ["ss", "-tlnp"], text=True, timeout=3, stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None

    for line in out.splitlines():
        if f":{port} " not in line:
            continue
        m = re.search(r'pid=(\d+)', line)
        if not m:
            continue
        pid = int(m.group(1))
        comm = "?"
        try:
            with open(f"/proc/{pid}/comm") as f:
                comm = f.read().strip()
        except Exception:
            pass
        return {"pid": pid, "comm": comm}
    return None


def _kill_llama_on_port(port: int) -> bool:
    """kill 占用指定端口的 llama-server。返回是否有进程被杀。"""
    occ = _check_port_occupied(port)
    if not occ:
        return False
    if "llama" not in occ["comm"].lower():
        return False

    try:
        os.killpg(os.getpgid(occ["pid"]), signal.SIGKILL)
    except Exception:
        try:
            os.kill(occ["pid"], signal.SIGKILL)
        except Exception:
            return False

    log_event("info", f"清理端口 {port} 上的残留 {occ['comm']} (pid={occ['pid']})",
              stage="preflight", event="preflight.port_cleaned",
              extra={"port": port, "pid": occ["pid"], "comm": occ["comm"]})
    return True


# ========== 主函数 ==========
def run_preflight(scope: str = "full",
                  auto_clean_ports: bool = True) -> Tuple[bool, List[Issue]]:
    issues: List[Issue] = []

    # ================= 核心动态感知闸门 =================
    is_ollama = (LLM_BACKEND == "ollama")
    is_cloud = (LLM_BACKEND == "cloud_api")
    use_local_llama = (LLM_BACKEND == "llamacpp_server")
    # ====================================================

    # ---- GPU ----
    # 只有在用本地 llama.cpp 时才检查 GPU
    if use_local_llama:
        gpu_issue = _check_gpu()
        if gpu_issue:
            issues.append(gpu_issue)

    # ---- 本地 llama-server 文件 ----
    if use_local_llama:
        if not os.path.exists(LLAMACPP_BIN):
            issues.append(("fatal", "llama-server", f"二进制不存在: {LLAMACPP_BIN}"))

        for name, path in [
            ("9B 模型", LLAMACPP_MODEL),
            ("1.5B 模型", ROUTER_SERVER_MODEL),
        ]:
            issue = _check_file(path, name)
            if issue:
                issues.append(issue)

        # 端口检查（只看本地 llama.cpp 的端口）
        for port in (LLAMACPP_PORT, ROUTER_SERVER_PORT):
            occ = _check_port_occupied(port)
            if occ:
                if auto_clean_ports and "llama" in occ["comm"].lower():
                    if _kill_llama_on_port(port):
                        log_event("info", f"端口 {port} 残留已清理",
                                  stage="preflight", event="preflight.port_auto_cleaned",
                                  extra={"port": port})
                    else:
                        issues.append(("fatal", f"端口 {port}",
                                       f"残留 {occ['comm']} (pid={occ['pid']}) 清理失败"))
                else:
                    issues.append(("warning", f"端口 {port}",
                                   f"被 {occ['comm']} (pid={occ['pid']}) 占用"))

    elif is_ollama:
        # 如果是 Ollama，尝试简单的探测服务是否可用（可选）
        try:
            import requests
            res = requests.get("http://localhost:11434/api/tags", timeout=3)
            if res.status_code != 200:
                issues.append(("warning", "Ollama", "服务未响应，请确保 'ollama serve' 正在运行"))
        except Exception:
            issues.append(("warning", "Ollama", "无法连接本地 Ollama 服务，请确保已安装并启动"))

    # ---- full 模式额外检查 ----
    if scope == "full":
        # 数据库
        try:
            from core.memory import get_store
            get_store().init()
        except Exception as e:
            issues.append(("fatal", "数据库", f"初始化失败: {e}"))

        # Playwright
        try:
            import playwright  # noqa: F401
        except ImportError:
            issues.append(("warning", "Playwright", "未安装，browser 工具不可用"))

        # Chromium binary（可选）
        if CHROME_BIN and not os.path.exists(CHROME_BIN):
            issues.append(("warning", "Chromium", f"binary 不存在: {CHROME_BIN}（Playwright 自带的仍可用）"))

        # 磁盘
        try:
            st = shutil.disk_usage(DATA_DIR)
            free_gb = st.free / (1024 ** 3)
            if free_gb < 1:
                issues.append(("warning", "磁盘", f"可用空间不足: {free_gb:.2f}GB"))
        except Exception:
            pass

    has_fatal = any(level == "fatal" for level, _, _ in issues)
    return (not has_fatal), issues


def format_issues(issues: List[Issue]) -> str:
    """格式化 issues 列表供终端显示。"""
    if not issues:
        return "✅ 所有检查通过"
    lines = []
    for level, name, msg in issues:
        tag = "❌" if level == "fatal" else "⚠️ "
        lines.append(f"{tag} [{name}] {msg}")
    return "\n".join(lines)