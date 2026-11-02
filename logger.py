"""
日志模块（纯增量，不破坏现有调用）

字段规范：
- stage:  模块维度，取值 agent / route / llm / tool / ctx / io
- event:  事件维度，取值见下表
- extra:  结构化数据，按 event 决定带哪些字段

事件 → 字段映射：

  agent.start     hint, max_attempts, summary
  agent.round     round
  agent.done      round, reason
  route.decision  hint, conf, keywords, summary
  route.fallback  error
  llm.call        backend, model, messages, tools
  llm.done        backend, model, done_reason, elapsed_ms,
                  eval_count, prompt_eval_count, tool_calls
  llm.empty       backend, model, attempt, prompt_eval_count, done_reason
  llm.error       backend, model, error, elapsed_ms
  tool.call       tool, args
  tool.result     tool, status, elapsed_ms, exit_code, output_len, output_truncated
  ctx.budget      tokens_est, limit, trimmed, kept_turns
  confirm.request command

status 取值固定：ok / error / timeout / refused / cancelled

用法（新代码）：
    log_event("info", "tool call", stage="tool", event="tool.call",
              extra={"tool": "execute_command", "args": {...}})

用法（老代码，仍兼容）：
    log_event("info", "agent 第 1/50 轮", stage="tool_call")
"""

import os
import sys
import json
from datetime import datetime

from config import LOG_DIR, LOG_FILE


# 只初始化一次，避免每行日志都 makedirs
_initialized = False


def _ensure_log_dir():
    global _initialized
    if _initialized:
        return
    os.makedirs(LOG_DIR, exist_ok=True)
    _initialized = True


def log_event(level, message, stage=None, event=None, extra=None, console=None):
    """
    level:   "debug" / "info" / "warning" / "error"
    message: 人类可读摘要，不要塞结构化数据
    stage:   模块维度（agent / route / llm / tool / ctx / io）
    event:   事件维度（agent.start / tool.call / llm.done ...）
    extra:   结构化字段 dict
    console: 兼容旧代码的 CLI 渲染覆写；新代码不要用
    """
    ts = datetime.now()
    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
    ts_iso = ts.isoformat(timespec="seconds")

    # CLI 渲染
    if console is not None:
        print(console)
    else:
        print(f"[{ts_str}] [{level.upper()}] {message}")

    entry = {
        "ts": ts_iso,
        "level": level,
        "stage": stage,
        "event": event,
        "message": message,
    }
    if extra:
        entry["extra"] = extra

    try:
        _ensure_log_dir()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[logger] write failed: {e}", file=sys.stderr)