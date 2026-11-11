import json
import os
import collections
from config import LOG_FILE, HISTORY_RESULT_TRUNCATE

def read_recent_turns(limit: int = 10) -> list:
    """从 agent.jsonl 提取最近 N 轮“动作序列”的历史（毫秒级尾部读取）。"""
    if not os.path.exists(LOG_FILE):
        return []

    turns = []
    current_turn = None

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        # 使用 deque 只保留最后 500 行，防止日志过大卡死
        last_lines = collections.deque(f, maxlen=500)
        
        for line in last_lines:
            try:
                e = json.loads(line)
            except Exception:
                continue

            stage = e.get("stage")
            msg = e.get("message", "")
            
            if e.get("level") == "debug":
                continue

            if stage == "input":
                if current_turn and current_turn.get("user_input"):
                    turns.append(current_turn)
                current_turn = {
                    "user_input": msg.replace("用户指令: ", "").strip(),
                    "intent_summary": "",
                    "steps": [],
                    "reply": "",
                    "ts": e.get("ts", "")  # 抓取时间戳
                }

            elif current_turn:
                if stage == "route" and "|" in msg:
                    current_turn["intent_summary"] = msg.split("|")[-1].strip()
                
                elif stage == "tool_call" and msg.startswith("执行工具:"):
                    try:
                        tool_part = msg.split("执行工具: ")[1].split(",")[0].strip()
                        args = e.get("extra", {}).get("args", {})
                        current_turn["steps"].append({
                            "type": "call",
                            "tool": tool_part,
                            "args": str(args)[:100]
                        })
                    except Exception:
                        pass
                
                elif stage == "tool_result":
                    res_preview = msg[:HISTORY_RESULT_TRUNCATE] + ("..." if len(msg) > HISTORY_RESULT_TRUNCATE else "")
                    current_turn["steps"].append({
                        "type": "result",
                        "content": res_preview
                    })

                elif stage == "reply":
                    current_turn["reply"] = msg[:200]

        if current_turn and current_turn.get("user_input"):
            turns.append(current_turn)

    return turns[-limit:]