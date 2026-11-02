"""
上下文压缩。

职责：
- 判断是否需要压缩
- 提取待压缩轮次
- 调 LLM 生成摘要（LLM 由调用方注入）
- 写入 MemoryStore

不 import 任何 LLM 层，通过 llm_caller 参数解耦，便于测试。
"""

from logger import log_event


SUMMARY_SYSTEM_PROMPT = "你是一个对话摘要生成器，输出简洁的中文摘要。"

SUMMARY_USER_TEMPLATE = """请把下面这些对话轮次压缩成一段简短的中文摘要，保留：
- 用户的核心需求
- 已经完成的事
- 未完成的事（如果有）
- 关键上下文（文件路径、参数、工具名等）

不要超过 {max_chars} 字。直接输出摘要正文，不要任何前缀，不要 markdown 格式。

---
{dialog_text}
---
"""


def _format_turns(turns: list) -> str:
    lines = []
    for t in turns:
        lines.append(f"用户: {t.get('user_input') or ''}")
        if t.get("intent_summary"):
            lines.append(f"  意图: {t['intent_summary']}")
        if t.get("tool"):
            lines.append(f"  工具: {t['tool']}")
        if t.get("result"):
            r = (t["result"] or "")[:200]
            lines.append(f"  结果: {r}")
        lines.append("")
    return "\n".join(lines)


def maybe_compress(store, llm_caller,
                   trigger_at: int = 12,
                   keep_recent: int = 8,
                   max_chars: int = 300):
    """
    检查是否需要压缩。需要则生成摘要并标记老轮次。

    参数：
      store        : MemoryStore 实例
      llm_caller   : callable(messages, tools=None, retry=False) -> dict
                     和 core.llm.call_planner 签名兼容
      trigger_at   : 未压缩轮次 > 此值时触发
      keep_recent  : 压缩后保留最近 N 轮
      max_chars    : 摘要长度上限

    返回：(是否压缩, 摘要文本 or None)
    """
    unsummarized = store.get_unsummarized_turns()

    if len(unsummarized) <= trigger_at:
        return False, None

    # 保留最近 keep_recent 轮，压缩更早的
    to_compress = unsummarized[:-keep_recent] if keep_recent > 0 else unsummarized
    if not to_compress:
        return False, None

    log_event("info",
              f"触发上下文压缩：{len(to_compress)} 轮 → 摘要",
              stage="memory", event="memory.compress.start",
              extra={"to_compress": len(to_compress),
                     "keep_recent": keep_recent})

    dialog_text = _format_turns(to_compress)
    prompt = SUMMARY_USER_TEMPLATE.format(
        max_chars=max_chars,
        dialog_text=dialog_text,
    )

    result = llm_caller(
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        tools=None,
        retry=False,
    )

    if "error" in result:
        log_event("warning",
                  f"摘要生成失败: {result.get('error')}",
                  stage="memory", event="memory.compress.error",
                  extra={"error": result.get("error")})
        return False, None

    summary_text = (result.get("message", {}).get("content") or "").strip()
    if not summary_text:
        log_event("warning", "摘要为空，放弃压缩",
                  stage="memory", event="memory.compress.empty")
        return False, None

    turn_ids = [t["id"] for t in to_compress]
    store.save_summary(summary_text, turn_ids)
    store.mark_turns_summarized(turn_ids)

    log_event("info",
              f"压缩完成：{len(to_compress)} 轮 → {len(summary_text)} 字",
              stage="memory", event="memory.compress.done",
              extra={"compressed_turns": len(to_compress),
                     "summary_len": len(summary_text)})

    return True, summary_text