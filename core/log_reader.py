import json
import os
from config import LOG_FILE

def read_recent_turns(limit: int = 10) -> list:
    """从 agent.jsonl 提取最近 N 轮“动作序列”的历史。"""
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

            stage = e.get("stage")
            msg = e.get("message", "")
            event = e.get("event")

            # 过滤 debug，只留 info/warning/error
            if e.get("level") == "debug":
                continue

            # 遇到新的用户输入，开始新一轮
            if stage == "input":
                if current_turn and current_turn.get("user_input"):
                    turns.append(current_turn)
                current_turn = {
                    "user_input": msg.replace("用户指令: ", "").strip(),
                    "intent_summary": "",
                    "steps": [],      # 存多步动作
                    "reply": ""
                }

            elif current_turn:
                # 提取意图
                if stage == "route" and "|" in msg:
                    current_turn["intent_summary"] = msg.split("|")[-1].strip()
                
                # 提取工具调用（跳过"agent 第 N 轮"的废话）
                elif stage == "tool_call" and msg.startswith("执行工具:"):
                    try:
                        # 格式：执行工具: execute_command, 参数: {...}
                        tool_part = msg.split("执行工具: ")[1].split(",")[0].strip()
                        args = e.get("extra", {}).get("args", {})
                        current_turn["steps"].append({
                            "type": "call",
                            "tool": tool_part,
                            "args": str(args)[:100]  # 参数截断，防爆
                        })
                    except Exception:
                        pass
                
                # 提取工具结果
                elif stage == "tool_result":
                    # msg 格式：execute_command → ✅ 命令执行成功...
                    # 截断到 150 字，防爆
                    res_preview = msg[:150] + ("..." if len(msg) > 150 else "")
                    current_turn["steps"].append({
                        "type": "result",
                        "content": res_preview
                    })

                # 提取最终回复
                elif stage == "reply":
                    current_turn["reply"] = msg[:200]

        # 补上最后一条
        if current_turn and current_turn.get("user_input"):
            turns.append(current_turn)

    return turns[-limit:]