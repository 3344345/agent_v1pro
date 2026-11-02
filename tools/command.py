import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog

from registries.tool_registry import register
from core.executor import execute_command as _exec
from runtime.stop_token import get_current
from logger import log_event


def _has_display() -> bool:
    """Linux 无 DISPLAY/WAYLAND_DISPLAY 时 Tk 会崩。"""
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def _confirm_callback(command: str):
    """弹出独立 Tk 窗口确认。返回 (confirmed, password)。"""
    if not _has_display():
        log_event("error", "无图形环境，无法弹确认窗口",
                  stage="confirm", event="confirm.no_display")
        return False, None

    try:
        root = tk.Tk()
        root.withdraw()
    except Exception as e:
        log_event("error", f"Tk 初始化失败: {e}",
                  stage="confirm", event="confirm.tk_error")
        return False, None

    try:
        # ---- 确认 ----
        log_event("warning", f"命令需要确认: {command}",
                  stage="confirm", event="confirm.request",
                  extra={"command": command[:200]})

        display = command if len(command) <= 500 else command[:500] + "…"
        confirmed = messagebox.askyesno(
            title="Agent 命令确认",
            message=f"Agent 请求执行：\n\n{display}\n\n是否允许？",
            icon="warning",
            parent=root,
        )
        if not confirmed:
            log_event("info", "用户拒绝执行",
                      stage="confirm", event="confirm.denied")
            return False, None

        log_event("info", "用户确认执行",
                  stage="confirm", event="confirm.accepted")

        # ---- sudo 密码 ----
        password = None
        if "sudo" in command:
            password = os.environ.get("AGENT_SUDO_PASS")
            if not password:
                password = simpledialog.askstring(
                    title="Agent sudo 密码",
                    prompt="输入 sudo 密码：",
                    show="*",
                    parent=root,
                )
                if not password:
                    log_event("warning", "密码为空，取消执行",
                              stage="confirm", event="confirm.no_password")
                    return False, None

        return True, password
    finally:
        try:
            root.destroy()
        except Exception:
            pass


@register(
    name="execute_command",
    description="执行系统命令行。用于文件操作、下载、检测、安装等。危险命令会请求确认。",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的命令，如 'ls ~/Desktop' 或 'wget -O /tmp/x.zip https://...'"
            }
        },
        "required": ["command"],
    },
    requires_network=False,
)
def execute_command(command: str) -> str:
    if not command or not command.strip():
        return "❌ 未提供命令"

    result = _exec(
        command,
        timeout=60,
        confirm_callback=_confirm_callback,
        stop_token=get_current(),
    )

    if result.rejected_reason:
        return f"❌ 命令被拒绝: {result.rejected_reason}"

    if result.success:
        msg = f"✅ 命令执行成功（退出码 {result.exit_code}）"
        if result.stdout:
            msg += f"\n输出:\n{result.stdout[:1500]}"
        if result.created_files:
            msg += f"\n创建了 {len(result.created_files)} 个文件: {', '.join(result.created_files[:5])}"
        if result.modified_files:
            msg += f"\n修改了 {len(result.modified_files)} 个文件: {', '.join(result.modified_files[:5])}"
        return msg
    else:
        msg = f"❌ 命令执行失败（退出码 {result.exit_code}）"
        if result.stderr:
            msg += f"\n错误: {result.stderr[:1000]}"
        return msg