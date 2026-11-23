"""云端 API 后端（OpenAI 兼容接口）"""
import json
import requests
from config import CLOUD_API_BASE, CLOUD_API_KEY, CLOUD_MODEL_NAME, TIMEOUT
from core.llm.base import LLMBackend
from logger import log_event


class CloudApiBackend(LLMBackend):
    def __init__(self, profile: str = "planner", *args, **kwargs):
        self.profile = profile
        self.session = requests.Session()

    @staticmethod
    def _normalize_messages(messages, thinking_enabled: bool):
        """发送前规整历史消息，规避云端两类 4xx：
          1) thinking 模式要求历史 assistant 必须回传 reasoning_content（缺失补 ""）
          2) role=tool 必须带 tool_call_id（缺失则按序回填最近的 call id）
        """
        out, pending_tool_ids, seq = [], [], 0
        missing_reasoning = False
        for m in messages or []:
            if not isinstance(m, dict):
                continue
            msg = dict(m)
            role = msg.get("role")
            if msg.get("content") is None:
                msg["content"] = ""

            if role == "assistant":
                tcs = msg.get("tool_calls") or []
                if tcs:
                    seq += 1
                    clean = []
                    for k, t in enumerate(tcs):
                        t = dict(t)
                        fn = dict(t.get("function") or {})
                        if not isinstance(fn.get("arguments"), str):
                            fn["arguments"] = json.dumps(fn.get("arguments") or {}, ensure_ascii=False)
                        t["function"] = fn
                        t.setdefault("type", "function")
                        if not t.get("id"):
                            t["id"] = f"call_{seq}_{k}"
                        clean.append(t)
                        pending_tool_ids.append(t["id"])
                    msg["tool_calls"] = clean
                    if thinking_enabled:
                        # 云端要求回传真实 reasoning_content；缺失时补空串仍会 400，
                        # 故标记缺失，由 chat() 决定是否降级关闭 thinking。
                        if not msg.get("reasoning_content"):
                            missing_reasoning = True
                        msg["reasoning_content"] = msg.get("reasoning_content") or ""
                else:
                    # 关键修复：assistant 无工具调用时必须彻底移除 tool_calls，
                    # 否则云端会因 tool_calls=[] 报 400 (empty array)
                    msg.pop("tool_calls", None)
                    if thinking_enabled:
                        msg["reasoning_content"] = msg.get("reasoning_content") or ""
                    else:
                        msg.pop("reasoning_content", None)


            elif role == "tool":
                if not msg.get("tool_call_id") and pending_tool_ids:
                    msg["tool_call_id"] = pending_tool_ids.pop(0)
            out.append(msg)

        # 最后一道防线：保证 assistant(tool_calls) 与 role=tool 严格配对。
        # 云端硬性要求每个 tool_call_id 都必须有且仅有一条 tool 响应，
        # 否则直接 400。这里做两件事：
        #   1) 为缺失响应的 tool_call 补占位 tool 消息；
        #   2) 丢弃找不到对应 tool_call 的孤立 tool 消息。
        fixed, i = [], 0
        n = len(out)
        while i < n:
            m = out[i]
            fixed.append(m)
            if m.get("role") == "assistant" and m.get("tool_calls"):
                want_ids = [t.get("id") for t in m["tool_calls"]]
                # 收集紧随其后的连续 tool 消息
                j = i + 1
                got = {}
                while j < n and out[j].get("role") == "tool":
                    tid = out[j].get("tool_call_id")
                    if tid in want_ids and tid not in got:
                        got[tid] = out[j]
                    j += 1
                # 按 tool_calls 顺序补齐，缺失的补占位
                for tid in want_ids:
                    if tid in got:
                        fixed.append(got[tid])
                    else:
                        fixed.append({
                            "role": "tool",
                            "tool_call_id": tid,
                            "content": "（该工具调用无响应，已由系统补占位）",
                        })
                i = j
                continue
            if m.get("role") == "tool":
                # 走到这里说明是孤立 tool（前面没有 assistant tool_calls），丢弃
                fixed.pop()
            i += 1
        return fixed, missing_reasoning

    def chat(self, model, messages, tools=None, options=None, timeout=None) -> dict:
        from config import CLOUD_THINKING
        real_model = CLOUD_MODEL_NAME
        url = f"{CLOUD_API_BASE.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {CLOUD_API_KEY}",
            "Content-Type": "application/json"
        }

        thinking_enabled = str(CLOUD_THINKING).strip().lower() not in ("0", "off", "false", "disabled", "no")
        opts = options or {}
        norm_messages, missing_reasoning = self._normalize_messages(messages, thinking_enabled)
        # 降级保护：thinking 开启但历史 assistant 缺真实 reasoning_content 时，
        # 云端必然 400。此时自动关闭 thinking 规避，保证请求可用。
        if thinking_enabled and missing_reasoning:
            thinking_enabled = False
            log_event("warning", f"[{self.profile}] 历史缺少 reasoning_content，本轮自动降级关闭 thinking 以规避 400", stage="llm")
        payload = {
            "model": real_model,
            "messages": norm_messages,
            "temperature": opts.get("temperature", 0.1),
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if not thinking_enabled:
            payload["thinking"] = {"type": "disabled"}

        try:
            resp = self.session.post(url, headers=headers, json=payload, timeout=timeout or TIMEOUT)
            if resp.status_code >= 400:
                body = (resp.text or "")[:800]
                log_event("error", f"[{self.profile}] 云端 API HTTP {resp.status_code}: {body}", stage="llm")
                return {"error": f"HTTP {resp.status_code}: {body}"}

            data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}

            return {
                "message": {
                    "content": msg.get("content") or "",
                    "tool_calls": msg.get("tool_calls") or [],
                    "reasoning_content": msg.get("reasoning_content") or "",
                },
                "done_reason": choice.get("finish_reason"),
            }
        except Exception as e:
            log_event("error", f"[{self.profile}] 云端 API 调用失败: {e}", stage="llm")
            return {"error": str(e)}

    def embed(self, model, texts):
        # 云端接口通常不用于本地向量化，直接返回空
        return []

    def is_available(self) -> bool:
        # 假设只要配置了 Key 就可用（实际中可发个空请求探活）
        return bool(CLOUD_API_KEY and CLOUD_API_KEY != "your-api-key-here")

    def close(self) -> None:
        try:
            self.session.close()
        except Exception:
            pass