"""
上下文拼接（纯函数）。

输入：MemoryStore 实例
输出：system message 用的字符串

历史记录来源：agent.jsonl（按需机械过滤，提取多步动作）。
加入时间感知：超过 15 分钟的历史会触发状态失效警告。
"""

import os
import json
from datetime import datetime
from config import HISTORY_LIMIT, HISTORY_RESULT_TRUNCATE, LOG_FILE


def _read_recent_turns_from_log(limit: int) -> list:
    """从 agent.jsonl 提取最近 N 轮的动作序列。"""
    if not os.path.exists(LOG_FILE):
        return []

    turns = []
    current_turn = None

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except Exception:
                continue

            if e.get("level") == "debug":
                continue

            stage = e.get("stage")
            msg = e.get("message", "")

            if stage == "input":
                if current_turn and current_turn.get("user_input"):
                    turns.append(current_turn)
                current_turn = {
                    "user_input": msg.replace("用户指令: ", "").strip(),
                    "intent_summary": "",
                    "steps": [],
                    "reply": "",
                    "ts": e.get("ts", "")  # <--- 记录时间戳
                }

            elif current_turn:
                if stage == "route" and "|" in msg:
                    current_turn["intent_summary"] = msg.split("|")[-1].strip()
                
                elif stage == "tool_call" and msg.startswith("执行工具:"):
                    try:
                        tool_part = msg.split("执行工具: ")[1].split(",")[0].strip()
                        args = e.get("extra", {}).get("args", {})
                        args_str = str(args)
                        if len(args_str) > 100:
                            args_str = args_str[:100] + "..."
                        current_turn["steps"].append({
                            "type": "call",
                            "tool": tool_part,
                            "args": args_str
                        })
                    except Exception:
                        pass
                
                elif stage == "tool_result":
                    res_preview = msg[:150] + ("..." if len(msg) > 150 else "")
                    current_turn["steps"].append({
                        "type": "result",
                        "content": res_preview
                    })

                elif stage == "reply":
                    current_turn["reply"] = msg[:200]

        if current_turn and current_turn.get("user_input"):
            turns.append(current_turn)

    return turns[-limit:]


def build_focus_context(store, max_result: int = 800) -> str:
    parts = []

    # ---------- 0. 任务锚点 ----------
    anchor_turns = _read_recent_turns_from_log(limit=3)
    if not anchor_turns:
        anchor_turns = store.get_recent_turns(limit=3, only_unsummarized=False)
        
    session = store.get_session()
    current_input = session.get("last_user_input") if session else ""

    if current_input or anchor_turns:
        parts.append("[任务锚点]")
        for i, t in enumerate(anchor_turns, 1):
            ui = (t.get("user_input") or "").strip().replace("\n", " ")
            if len(ui) > 60:
                ui = ui[:60] + "..."
            parts.append(f"  {i}. {ui}")
        if current_input:
            ui = current_input.strip().replace("\n", " ")
            if len(ui) > 60:
                ui = ui[:60] + "..."
            parts.append(f"  当前: {ui}")
        parts.append("")

    # ---------- 1. 历史摘要 ----------
    summaries = store.get_summaries()
    if summaries:
        parts.append("[历史摘要]")
        for s in summaries[-3:]:
            parts.append(f"  {s['summary'][:100]}...")
        parts.append("")

    # ---------- 2. 最近 N 轮（带时间感知） ----------
    turns = _read_recent_turns_from_log(limit=6)
    if not turns:
        turns = store.get_recent_turns(limit=6, only_unsummarized=True)

    if turns:
        parts.append(f"[最近 {len(turns)} 轮]")
        
        # --- 时间感知核心逻辑 ---
        time_gap_str = ""
        last_ts_str = turns[-1].get("ts")
        if last_ts_str:
            try:
                # 兼容可能带或不带秒的 ISO 格式
                last_time = datetime.fromisoformat(last_ts_str)
                delta_minutes = (datetime.now() - last_time).total_seconds() / 60
                if delta_minutes > 15:
                    if delta_minutes > 1440:
                        time_gap_str = f"{int(delta_minutes // 1440)} 天"
                    elif delta_minutes > 60:
                        time_gap_str = f"{int(delta_minutes // 60)} 小时"
                    else:
                        time_gap_str = f"{int(delta_minutes)} 分钟"
                    
                    parts.append(
                        f"⚠️ 注意：距离上次任务已过去 {time_gap_str}。"
                        "过去的执行结果（如文件列表、网络状态）可能已失效，"
                        "如果涉及环境现状，请重新调用工具验证。"
                    )
            except Exception:
                pass
        # -------------------------

        for i, t in enumerate(turns, 1):
            prefix = f"[{time_gap_str}前] " if time_gap_str and i == 1 else ""
            line = f"  {i}. {prefix}用户: {t['user_input'][:80]}"
            if t.get("intent_summary"):
                line += f" | 意图: {t['intent_summary'][:40]}"
            parts.append(line)
            
            if t.get("steps"):
                steps = t["steps"]
                if len(steps) > 6:
                    steps = steps[:3] + [{"type": "result", "content": "...(中间步骤省略)..."}] + steps[-3:]
                
                for step in steps:
                    if step["type"] == "call":
                        parts.append(f"     🔧 {step['tool']} (参数: {step['args']})")
                    elif step["type"] == "result":
                        parts.append(f"     ↳ {step['content']}")
            else:
                if t.get("tool"):
                    parts.append(f"     🔧 {t['tool']}")
                if t.get("result"):
                    parts.append(f"     ↳ {t['result'][:100]}")

            if t.get("reply"):
                parts.append(f"     答: {t['reply'][:100]}")

    # ---------- 3. 上一轮详情（session，极简版） ----------
    if session and session.get("status") not in (None, "idle"):
        parts.append("")
        parts.append("[上一轮详情]")
        if session.get("last_result"):
            parts.append(f"结果: {session['last_result'][:200]}")

        artifacts = session.get("artifacts")
        if artifacts and isinstance(artifacts, str):
            try: artifacts = json.loads(artifacts)
            except Exception: artifacts = None
            
        if isinstance(artifacts, dict):
            sr = artifacts.get("search_results")
            if sr and isinstance(sr, list):
                parts.append("搜索结果:")
                for i, r in enumerate(sr[:2], 1):
                    parts.append(f"  {i}. {r.get('title', '?')[:30]} - {r.get('url', '')[:50]}")
                    c = (r.get("content", "") or "")[:50]
                    if c: parts.append(f"     {c}...")

    return "\n".join(parts)