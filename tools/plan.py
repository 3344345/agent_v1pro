from registries.tool_registry import register
from tools.context import get_context


@register(
    name="plan_todos",
    description=(
        "为复杂任务创建待办列表。只在任务需要 3 步以上时调用。\n"
        "创建后你会看到待办列表；每完成一步，再次调用本工具更新状态。\n"
        "简单任务（1-2 步）不要调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "description": "待办步骤列表，每项含 step / status / result",
                "items": {
                    "type": "object",
                    "properties": {
                        "step":   {"type": "string", "description": "可执行动作描述"},
                        "status": {"type": "string", "description": "pending / in_progress / done"},
                        "result": {"type": "string", "description": "该步结果摘要，未完成时留空"},
                    },
                    "required": ["step", "status"],
                },
            }
        },
        "required": ["todos"],
    },
)
def plan_todos(todos: list) -> str:
    if not isinstance(todos, list) or not todos:
        return "❌ todos 不能为空"

    cleaned = []
    for t in todos:
        if not isinstance(t, dict) or not t.get("step"):
            continue
        cleaned.append({
            "step": t.get("step", ""),
            "status": t.get("status", "pending"),
            "result": t.get("result", ""),
        })

    if not cleaned:
        return "❌ todos 格式不对，每项必须含 step 字段"

    get_context().todos = cleaned

    lines = ["✅ 待办列表已更新："]
    for i, t in enumerate(cleaned, 1):
        mark = {"done": "✓", "in_progress": "→", "pending": "·"}.get(t["status"], "·")
        line = f"  {mark} {i}. [{t['status']}] {t['step']}"
        if t["result"]:
            line += f"  — {t['result'][:80]}"
        lines.append(line)

    done = sum(1 for t in cleaned if t["status"] == "done")
    lines.append(f"\n进度: {done}/{len(cleaned)}")
    return "\n".join(lines)