"""
对比 1.5B CPU vs 9B GPU 的 router 性能。

前提：两个 server 都已启动
  - 8081: 9B on GPU
  - 8082: 1.5B on CPU

用法：
  cd ~/projects/agent_v1pro
  python3 test_router_speed.py
"""

import time
import json
import requests


SYSTEM = """你是一个意图分析器。分析用户输入，输出 JSON 格式：{"intent_summary": "...", "keywords": [...], "complexity_hint": "low/medium/high", "confidence": "low/medium/high"}。

规则：
1. intent_summary 用一句话概括用户意图，不超过 50 字
2. keywords 提取 3-5 个关键词，去重，中文优先
3. complexity_hint 判断任务复杂度：
   - low：单步、直接能完成（打招呼、查 IP、读文件）
   - medium：2-3 步（下载+分析、写文件+运行）
   - high：需要规划、多步、涉及多工具（写完整程序、画图+报告）
4. confidence 是分析把握程度，低于 60% 用 low

只输出 JSON，不要任何解释。"""

USER = "帮我分析一下桌面上那个 iris.csv 文件，按 species 分组计算 sepal_length 的均值和标准差，然后画一张箱线图保存到桌面"


def test(url, label, runs=2):
    print(f"\n{'='*60}")
    print(f"  {label}  ({url})")
    print(f"{'='*60}")

    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        "max_tokens": 200,
        "temperature": 0,
        "stream": False,
    }

    for i in range(1, runs + 1):
        t0 = time.monotonic()
        try:
            r = requests.post(f"{url}/v1/chat/completions", json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  第 {i} 次: ❌ {e}")
            return
        elapsed = time.monotonic() - t0

        usage = data.get("usage", {})
        timings = data.get("timings", {})
        content = data["choices"][0]["message"]["content"]

        print(f"\n  第 {i} 次: {elapsed:.2f}s")
        print(f"    prompt_tokens    : {usage.get('prompt_tokens')}")
        print(f"    completion_tokens: {usage.get('completion_tokens')}")
        print(f"    cached_tokens    : {usage.get('prompt_tokens_details', {}).get('cached_tokens', 'N/A')}")
        if timings:
            print(f"    prefill          : {timings.get('prompt_per_second', 0):.1f} t/s")
            print(f"    generate         : {timings.get('predicted_per_second', 0):.1f} t/s")
        print(f"    输出前 100 字    : {content[:100]}")


if __name__ == "__main__":
    test("http://127.0.0.1:8082", "1.5B on CPU", runs=2)
    test("http://127.0.0.1:8081", "9B on GPU", runs=2)