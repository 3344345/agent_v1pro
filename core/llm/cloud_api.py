"""云端 API 后端（OpenAI 兼容接口）"""
import requests
from config import CLOUD_API_BASE, CLOUD_API_KEY, CLOUD_MODEL_NAME, TIMEOUT
from core.llm.base import LLMBackend
from logger import log_event


class CloudApiBackend(LLMBackend):
    def __init__(self, profile: str = "planner", *args, **kwargs):
        self.profile = profile
        self.session = requests.Session()

    def chat(self, model, messages, tools=None, options=None, timeout=None) -> dict:
        from config import CLOUD_MODEL_NAME
        real_model = CLOUD_MODEL_NAME
        url = f"{CLOUD_API_BASE.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {CLOUD_API_KEY}",
            "Content-Type": "application/json"
        }
        
        opts = options or {}
        payload = {
            "model": real_model,
            "messages": messages,
            "temperature": opts.get("temperature", 0.1),
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = self.session.post(url, headers=headers, json=payload, timeout=timeout or TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            
            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            
            return {
                "message": {
                    "content": msg.get("content") or "",
                    "tool_calls": msg.get("tool_calls") or []
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