import time
from core.llm import get_backend, call_planner, reset_backend

# 1. 直接调后端
backend = get_backend()
print(f"backend type: {type(backend).__name__}")

t0 = time.monotonic()
result = backend.chat(
    model="local",
    messages=[{"role": "user", "content": "你好，用一句话介绍你自己"}],
    options={"temperature": 0.7, "num_predict": 256},
    timeout=120,
)
elapsed = round(time.monotonic() - t0, 2)
print(f"elapsed: {elapsed}s")

if "error" in result:
    print(f"ERROR: {result['error']}")
else:
    print(f"--- 回复 ---")
    print(result["message"]["content"])
    print(f"--- tokens: prompt={result.get('prompt_eval_count')} "
          f"eval={result.get('eval_count')} ---")

# 2. 走 call_planner（带空响应兜底）
result2 = call_planner(
    messages=[{"role": "user", "content": "写一句话描述今天的天气"}],
    tools=None,
    retry=False,
)
print(f"\n--- call_planner ---")
print(result2.get("message", {}).get("content") or result2)

reset_backend()
