"""上下文预算守卫：按真实 token 窗口裁剪 prompt。

为什么需要它：
    llama.cpp 在 prompt 超过 --ctx-size 时会静默截断（通常先丢头部），
    于是系统提示里的工具契约 / 护栏最先蒸发，这是小模型行为崩坏的主因。
    因此预算必须从 CONTEXT_WINDOW_TOKENS 派生，而不是散落各处的魔法字符数。

职责边界：
    只做"token 估算 + 裁剪"，不碰后端、不写日志、不做 IO。
    调度方（core/llm/__init__.py、main.py）负责记录压缩事件。
"""

import json
from typing import List

from config import (
    SHRINK_MAX_CHARS, SYS_HEAD_RATIO,
)

# 经验换算：ASCII（英文/代码）≈3 字符/token，CJK ≈1.4 字/token。
# 取偏保守的值，宁可多估也不让 prompt 溢出。
_ASCII_CHARS_PER_TOKEN = 3.0
_CJK_CHARS_PER_TOKEN = 1.4

# 最近几条工具结果保持完整（它们是当前任务的现场）；更老的逐级压缩。
PROTECT_LAST_TOOL_RESULTS = 2

_OMIT = "…[内容因窗口预算被省略]"
_TRUNC_FLOOR = 200
_TRUNC = "…[截断]"


def _flatten_text(obj) -> str:
    """把多模态 content（str / list[dict] / dict）压平成纯文本用于估算。

    OpenAI 多模态格式：content = [{"type":"text","text":...},
                                  {"type":"image_url","image_url":{...}}]
    图片块本身不计字符（token 由后端按图计），只取文本部分。
    """
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        # 文本块取 text；图片块跳过（避免把 base64 当文本算爆）
        if obj.get("type") == "image_url" or "image_url" in obj:
            return ""
        return _flatten_text(obj.get("text") or obj.get("content") or "")
    if isinstance(obj, (list, tuple)):
        return "".join(_flatten_text(x) for x in obj)
    return str(obj)


def estimate_tokens(text) -> int:
    """粗略估算 token 数（不依赖 tokenizer，跨后端通用）。

    兼容 str 与多模态 list/dict 结构。
    """
    text = _flatten_text(text)
    if not text:
        return 0
    ascii_n = 0
    other_n = 0
    for ch in text:
        if ord(ch) < 128:
            ascii_n += 1
        else:
            other_n += 1
    return int(ascii_n / _ASCII_CHARS_PER_TOKEN + other_n / _CJK_CHARS_PER_TOKEN) + 1


def estimate_messages_tokens(messages: List[dict]) -> int:
    """估算整组 messages 的 token 数（含 role 与 tool_calls 的 JSON 体积）。"""
    total = 0
    for m in messages or []:
        total += 8  # role / 结构开销
        total += estimate_tokens(m.get("content") or "")
        tool_calls = m.get("tool_calls")
        if tool_calls:
            try:
                total += estimate_tokens(json.dumps(tool_calls, ensure_ascii=False))
            except (TypeError, ValueError):
                total += 64
    return total + 16


def fit_system(content: str, budget_tokens: int) -> str:
    """系统提示超预算时保留头部结论 + 尾部细节，中段省略。

    头部放身份/规则，尾部放工具契约与注入的技能/记忆，两者都不能丢。
    """
    if not content:
        return content
    if estimate_tokens(content) <= budget_tokens:
        return content

    head_len = int(len(content) * SYS_HEAD_RATIO)
    head = content[:head_len]
    # 二分查找尾部最多能保留多少字符，保证估算总量不超预算
    lo, hi = 0, len(content) - head_len
    while lo < hi:
        mid = (lo + hi + 1) // 2
        candidate = head + "\n\n" + _OMIT + "\n\n" + content[-mid:] if mid else head + "\n\n" + _OMIT
        if estimate_tokens(candidate) <= budget_tokens:
            lo = mid
        else:
            hi = mid - 1
    return head + "\n\n" + _OMIT + "\n\n" + content[-lo:] if lo else head + "\n\n" + _OMIT


def _truncate_tools(messages: List[dict], limit_chars: int, protect_last: int) -> None:
    """把非受保护的 tool 消息压到 limit_chars（<=0 表示整条省略）。"""
    protected = set()
    seen = 0
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "tool":
            if seen < protect_last:
                protected.add(i)
                seen += 1
    for i, m in enumerate(messages):
        if i in protected or m.get("role") != "tool":
            continue
        content = m.get("content") or ""
        if not isinstance(content, str):
            # 多模态/结构化 content 不在此处裁剪，避免破坏结构
            continue
        if limit_chars <= 0:
            m["content"] = _OMIT
        elif len(content) > limit_chars:
            m["content"] = content[:limit_chars] + _TRUNC


def _drop_oldest(messages: List[dict], keep_tail: int) -> bool:
    """丢掉最旧的一组非 system 消息，永远保留最近的 keep_tail 条。

    关键：assistant(tool_calls) 与其对应的 tool 结果必须成组删除。
    否则会留下孤立的 tool 消息（无对应 tool_calls）或悬空的 tool_calls
    （无对应 tool 结果），云端 API 会直接返回 400 Bad Request。
    """
    if len(messages) <= keep_tail + 1:
        return False
    # 只在受保护区之外找可删的起点
    limit = len(messages) - keep_tail
    for i in range(limit):
        m = messages[i]
        if m.get("role") == "system":
            continue
        # 计算这一"组"的结束位置（不含）
        end = i + 1
        if m.get("role") == "assistant" and m.get("tool_calls"):
            # 吞掉紧随其后的所有 tool 结果
            while end < len(messages) and messages[end].get("role") == "tool":
                end += 1
        elif m.get("role") == "tool":
            # 孤立 tool（理论上不该出现）：连同前面紧邻的 assistant 一起删
            start = i
            while start - 1 >= 0 and messages[start - 1].get("role") == "tool":
                start -= 1
            if start - 1 >= 0 and messages[start - 1].get("role") == "assistant":
                start -= 1
            del messages[start:end]
            return True
        # 若这一组会吃掉受保护的尾部，就放弃（避免破坏最近上下文）
        if end > limit:
            continue
        del messages[i:end]
        return True
    return False


def fit_messages(messages: List[dict], budget_tokens: int, keep_tail: int = 6) -> List[dict]:
    """把 messages 压进 budget_tokens；不超预算时原样返回（零拷贝）。

    压缩梯度（由轻到重，达标即停）：
        1. 老工具结果截到 SHRINK_MAX_CHARS
        2. 老工具结果截到 400 字符
        3. 老工具结果整条省略
        4. 仍超则从最旧的消息开始整条丢弃
    """
    if not messages:
        return messages
    if estimate_messages_tokens(messages) <= budget_tokens:
        return messages

    msgs = [dict(m) for m in messages]  # 浅拷贝，避免污染调用方的历史
    for limit in (SHRINK_MAX_CHARS, 400, 0):
        _truncate_tools(msgs, limit, PROTECT_LAST_TOOL_RESULTS)
        if estimate_messages_tokens(msgs) <= budget_tokens:
            return msgs

    while estimate_messages_tokens(msgs) > budget_tokens:
        if not _drop_oldest(msgs, keep_tail):
            break

    # 兜底：连"受保护的最近工具结果"也要压（逐轮减半，200 字符为地板）
    while estimate_messages_tokens(msgs) > budget_tokens:
        shrunk = False
        for m in msgs:
            if m.get("role") == "tool":
                content = m.get("content") or ""
                # 地板要算上 _TRUNC 后缀，否则每轮都"缩"成 206 字符，永远缩不完
                if len(content) > _TRUNC_FLOOR + len(_TRUNC):
                    m["content"] = content[:max(len(content) // 2, _TRUNC_FLOOR)] + _TRUNC
                    shrunk = True
        if not shrunk:
            break
    return msgs
