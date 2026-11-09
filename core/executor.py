import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Callable
from config import EXEC_SHELL
from core.sys_utils import start_process, kill_process_tree

# ========== 开发者防呆安全配置 ==========
BLACKLIST_PATTERNS = [
    # 1. 致命木马执行 (直接拒绝，不给确认机会)
    r"curl\s+.*\|\s*(bash|sh)",
    r"wget\s+.*\|\s*(bash|sh)",
    r"eval\s*\$\(",
    
    # 2. 核心资产破坏 (直接拒绝)
    r"\brm\s+-rf?\s+.*\.git",
    r"\brm\s+-rf?\s+/\s*$",
    r"\brm\s+-rf?\s+/\*",
    r"\brm\s+-rf?\s+~/?\s*$",
    r"\bmv\s+.*\.git",
    r"\bmkfs\b",
    r"\bdd\s+.*of=/dev/[sh]d",
    r">\s*/dev/[sh]d",
]

# 需要用户二次确认的关键词（在终端或 GUI 弹窗）
NEED_CONFIRM_KEYWORDS = [
    "sudo", 
    " rm ", "rm -", 
    "apt remove", "apt purge", "dpkg -i",
    "pip uninstall", "conda remove",
    "chmod 777", "chown", 
    " kill ", "pkill", "systemctl stop",
    "cat .env", "cat ~/.ssh", "cat /etc/shadow",
]

# 受保护的目录，写入时必须确认
PROTECTED_PATHS = [
    "/etc/", "/usr/", "/boot/", "/sys/", "/proc/", "/var/log/",
    ".git/", 
]
READONLY_COMMANDS = {
    "ls", "cat", "head", "tail", "wc", "grep", "find", "which", "file", "stat", "du", "df", "tree", "pwd", "whoami", "date", "uptime", "echo", "ping", "ps", "top", "free", "uname", "hostname", "id", "ip", "ifconfig", "netstat", "ss", "route", "traceroute", "nslookup", "dig", "host", "curl", "wget",
}

@dataclass
class CommandResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    created_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    rejected_reason: Optional[str] = None

def sanitize(text: str) -> str:
    if not text: return text
    for kw in ("password", "passwd", "token", "api_key", "secret"):
        text = re.sub(rf"(?i){kw}\s*[=:]\s*\S+", f"{kw}=***", text)
    return text

def is_safe_command(command: str) -> Tuple[bool, str]:
    for pat in BLACKLIST_PATTERNS:
        if re.search(pat, command): return False, f"命令匹配黑名单模式: {pat}"
    for path in PROTECTED_PATHS:
        if path in command and any(op in command for op in (">", ">>", " rm ", " mv ", " cp ")):
            return False, f"禁止写系统目录: {path}"
    return True, ""

def needs_confirmation(command: str) -> bool:
    cmd = f" {command} "
    return any(kw in cmd for kw in NEED_CONFIRM_KEYWORDS)

def is_readonly_command(command: str) -> bool:
    cmd = command.strip()
    if ">" in cmd: return False
    try: tokens = shlex.split(cmd)
    except ValueError: return False
    if not tokens: return True
    if any(f in tokens for f in ("-o", "-O", "--output", "-X")): return False
    first = os.path.basename(tokens[0])
    if first in READONLY_COMMANDS:
        if first in ("curl", "wget"): return "-o" not in tokens and "-O" not in tokens
        return True
    return False

def scan_directory(base: str = ".", max_depth: int = 3, max_files: int = 1000) -> dict:
    files = {}
    base_abs = os.path.abspath(base)
    base_depth = base_abs.rstrip("/").count("/")
    for root, dirs, filenames in os.walk(base_abs):
        depth = root.count("/") - base_depth
        if depth >= max_depth:
            dirs[:] = []
            continue
        for f in filenames:
            if len(files) >= max_files: return files
            full = os.path.join(root, f)
            try: files[full] = os.path.getmtime(full)
            except OSError: continue
    return files

def detect_changes(before: dict, after: dict) -> Tuple[List[str], List[str]]:
    created = [f for f in after if f not in before]
    modified = [f for f in after if f in before and after[f] > before[f]]
    return created, modified

def execute_command(command: str, timeout: int = 60, confirm_callback: Optional[Callable] = None, scan_before: Optional[bool] = None, log_fn: Optional[Callable] = None, stop_token=None) -> CommandResult:
    def _log(level, msg, extra=None):
        if log_fn: log_fn(level, msg, extra)

    safe, reason = is_safe_command(command)
    if not safe:
        _log("error", f"命令被拒绝: {reason}", {"command": sanitize(command)})
        return CommandResult(False, rejected_reason=reason, stderr=reason)

    password = None
    if needs_confirmation(command):
        if not confirm_callback:
            return CommandResult(False, rejected_reason="需要确认但无回调", stderr="需要确认")
        confirmed, password = confirm_callback(command)
        if not confirmed:
            return CommandResult(False, rejected_reason="用户拒绝", stderr="用户拒绝执行")

    if scan_before is None: scan_before = not is_readonly_command(command)
    before = scan_directory() if scan_before else {}

    use_stdin = bool(password and "sudo" in command)
    run_cmd = re.sub(r"\bsudo\b", "sudo -S", command, count=1) if use_stdin else command

    try:
        proc = start_process(
            run_cmd, shell=True, executable=EXEC_SHELL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if use_stdin else None, text=True,
        )
    except Exception as e:
        _log("error", "命令启动异常", {"command": sanitize(command), "error": str(e)})
        return CommandResult(False, stderr=str(e))

    if stop_token is not None: stop_token.register_proc(proc)

    stdout, stderr, timed_out = "", "", False
    try:
        try:
            stdout, stderr = proc.communicate(input=(password + "\n") if use_stdin else None, timeout=timeout)
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
        if stop_token is not None: stop_token.unregister_proc(proc)

    if stop_token is not None and stop_token.is_stopped():
        from runtime.stop_token import StopException
        raise StopException("用户按下停止按钮")

    if timed_out:
        _log("error", "命令超时", {"command": sanitize(command), "timeout": timeout})
        return CommandResult(False, stdout=sanitize(stdout), stderr=sanitize(stderr) + f"\n[系统强制终止] 命令超时（{timeout}秒）", exit_code=-9, rejected_reason="超时")

    created, modified = [], []
    if scan_before:
        after = scan_directory()
        created, modified = detect_changes(before, after)

    _log("info", "命令完成", {"command": sanitize(command), "exit_code": proc.returncode})
    return CommandResult(
        success=proc.returncode == 0, stdout=sanitize((stdout or "").strip()), stderr=sanitize((stderr or "").strip()),
        exit_code=proc.returncode, created_files=created, modified_files=modified,
    )