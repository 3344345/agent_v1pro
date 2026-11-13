from typing import Optional
from core.guardrails import BaseGuardrail, GuardrailContext
from config import TOOL_FAIL_INTERVENE_THRESHOLD, SIGNATURE_WINDOW_SIZE, SIGNATURE_DUP_THRESHOLD, SIMILARITY_ARGS_THRESHOLD, SIMILARITY_OUT_THRESHOLD
import difflib
import json

class ToolFailureGuardrail(BaseGuardrail):
    name = "连续失败熔断"
    def inspect(self, ctx: GuardrailContext) -> Optional[str]:
        if ctx.output.startswith("❌") or "Traceback" in ctx.output:
            ctx.state[f"fail_{ctx.tool_name}"] = ctx.state.get(f"fail_{ctx.tool_name}", 0) + 1
        else:
            ctx.state[f"fail_{ctx.tool_name}"] = 0
            
        if ctx.state[f"fail_{ctx.tool_name}"] >= TOOL_FAIL_INTERVENE_THRESHOLD:
            return f"⚠️ 系统干预：{ctx.tool_name} 工具已连续失败 {TOOL_FAIL_INTERVENE_THRESHOLD} 次。\n请立刻停止当前尝试，简述报错原因，并换一种命令或思路。"
        return None

class SemanticDuplicateGuardrail(BaseGuardrail):
    name = "语义相似度死循环"
    def inspect(self, ctx: GuardrailContext) -> Optional[str]:
        if not hasattr(self, "recent_actions"):
            from collections import deque
            self.recent_actions = deque(maxlen=SIGNATURE_WINDOW_SIZE)
            
        current_args_str = json.dumps(ctx.tool_args, sort_keys=True, ensure_ascii=False)
        similar_count = 0
        
        for prev_tool, prev_args_str, prev_out in self.recent_actions:
            if prev_tool == ctx.tool_name:
                sim_args = difflib.SequenceMatcher(None, current_args_str, prev_args_str).ratio()
                sim_out = difflib.SequenceMatcher(None, ctx.output, prev_out).ratio()
                if sim_args > SIMILARITY_ARGS_THRESHOLD or sim_out > SIMILARITY_OUT_THRESHOLD:
                    similar_count += 1
                    
        self.recent_actions.append((ctx.tool_name, current_args_str, ctx.output))
        
        if similar_count >= SIGNATURE_DUP_THRESHOLD:
            return f"⚠️ 系统干预：工具 {ctx.tool_name} 在最近 {SIGNATURE_WINDOW_SIZE} 次调用中，出现了 {similar_count} 次高度相似的参数或输出。请立刻停止此工具，汇报失败卡点并更换思路。"
        return None