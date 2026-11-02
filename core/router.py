import json
import re

from core.llm import call_router
from registries.intent_registry import get_examples


# ========== Prompt 模板 ==========
ROUTER_PROMPT_HEADER = """你是翻译官，把用户输入翻译成一句简洁的描述，并提取关键词、判断复杂度。

输出格式（只输出 JSON，不要解释）：
{{
  "intent_summary": "一句话描述用户想做什么（用中文）",
  "keywords": ["关键词1", "关键词2"],
  "complexity_hint": "low / medium / high",
  "confidence": "high / medium / low"
}}

complexity_hint 判断标准：
- low：0 或 1 次工具调用，单步完成
  （如"你好"、"看天气"、"列桌面文件"、"搜一下 XXX"）

- medium：2-4 步，执行路径事先确定，顺序执行，中途不需要改变计划
  每步的执行方式不依赖上一步的结果
  （如"搜 XXX 保存到文件"、"下载文件然后解压"）

- high：需要规划或迭代。满足以下任意一条：
  ① 步骤数超过 4
  ② 步骤之间有依赖，需要边做边看边调整
  ③ 涉及调试、试错、分析原因
  （如"检查 ZZZ 报错原因并修复"、"对比三份文档找出差异并总结"）
"""


def build_router_prompt(user_input: str, examples: list = None) -> str:
    if examples is None:
        examples = get_examples()

    parts = [ROUTER_PROMPT_HEADER, ""]
    for ex in examples[:6]:
        out = {
            "intent_summary": ex.get("summary", ""),
            "keywords": ex.get("keywords", []),
            "complexity_hint": ex.get("hint", "low"),
            "confidence": "high",
        }
        parts.append(f"用户输入：{ex['input']}")
        parts.append(f"输出：{json.dumps(out, ensure_ascii=False)}")
        parts.append("")

    parts.append(f"用户输入：{user_input}")
    parts.append("输出：")
    return "\n".join(parts)


# ========== 解析 ==========
def _strip_code_fence(text: str) -> str:
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    return m.group(1) if m else text


def _extract_json_object(text: str):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start:end + 1]


def parse_router_output(text: str) -> dict:
    if not text:
        return None

    text = _strip_code_fence(text.strip())
    text = _extract_json_object(text) or text

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    summary = data.get("intent_summary")
    if not isinstance(summary, str) or not summary.strip():
        return None

    keywords = data.get("keywords")
    if not isinstance(keywords, list):
        keywords = []
    keywords = [str(k) for k in keywords if k]

    hint = data.get("complexity_hint")
    if hint not in ("low", "medium", "high"):
        hint = "medium"

    confidence = data.get("confidence")
    if confidence not in ("high", "medium", "low"):
        confidence = "low"

    return {
        "intent_summary": summary.strip(),
        "keywords": keywords,
        "complexity_hint": hint,
        "confidence": confidence,
    }


# ========== 对外接口 ==========
def route(user_input: str, log_fn=None) -> dict:
    def _log(level, msg, extra=None):
        if log_fn:
            log_fn(level, msg, stage="route", extra=extra)

    if not user_input or not user_input.strip():
        return {"ok": False, "error": "空输入"}

    prompt = build_router_prompt(user_input.strip())
    messages = [{"role": "user", "content": prompt}]

    result = call_router(messages)

    if "error" in result:
        _log("error", f"router 调用失败: {result['error']}")
        return {"ok": False, "error": result["error"]}

    msg = result.get("message", {}) or {}
    raw = (msg.get("content") or "").strip()

    parsed = parse_router_output(raw)
    if not parsed:
        _log("warning", f"router 输出解析失败: {raw[:200]}")
        return {"ok": False, "error": "JSON 解析失败", "raw": raw}

    parsed["ok"] = True
    _log("info",
         f"路由: hint={parsed['complexity_hint']} conf={parsed['confidence']} "
         f"kw={parsed['keywords']} | {parsed['intent_summary'][:50]}")
    return parsed