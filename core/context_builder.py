import json
from datetime import datetime
from config import (
    HISTORY_INVALID_MINUTES, MEMORY_TOP_K, MEMORY_MIN_SCORE,
    ANCHOR_TURNS_LIMIT, SUMMARY_READ_LIMIT, RECENT_TURNS_LIMIT, HISTORY_STEP_LIMIT,
    SKILL_MIN_SCORE, SKILL_TRIGGER_MAP
)
from core.log_reader import read_recent_turns
from logger import log_event


def build_focus_context(store) -> str:
    """组装基于 session 和 日志 的 Focus 上下文。"""
    parts = []
    anchor_turns = read_recent_turns(limit=ANCHOR_TURNS_LIMIT)
    if not anchor_turns:
        anchor_turns = store.get_recent_turns(limit=ANCHOR_TURNS_LIMIT, only_unsummarized=False)
        
    session = store.get_session()
    current_input = session.get("last_user_input") if session else ""

    if current_input or anchor_turns:
        parts.append("[任务锚点]")
        for i, t in enumerate(anchor_turns, 1):
            ui = (t.get("user_input") or "").strip().replace("\n", " ")
            if len(ui) > 60: ui = ui[:60] + "..."
            parts.append(f"  {i}. {ui}")
        if current_input:
            ui = current_input.strip().replace("\n", " ")
            if len(ui) > 60: ui = ui[:60] + "..."
            parts.append(f"  当前: {ui}")
        parts.append("")

    summaries = store.get_summaries()
    if summaries:
        parts.append("[历史摘要]")
        for s in summaries[-SUMMARY_READ_LIMIT:]:
            parts.append(f"  {s['summary'][:100]}...")
        parts.append("")

    turns = read_recent_turns(limit=RECENT_TURNS_LIMIT)
    if not turns:
        turns = store.get_recent_turns(limit=RECENT_TURNS_LIMIT, only_unsummarized=True)

    if turns:
        parts.append(f"[最近 {len(turns)} 轮]")
        
        time_gap_str = ""
        last_ts_str = turns[-1].get("ts")
        if last_ts_str:
            try:
                last_time = datetime.fromisoformat(last_ts_str)
                delta_minutes = (datetime.now() - last_time).total_seconds() / 60
                if delta_minutes > HISTORY_INVALID_MINUTES:
                    if delta_minutes > 1440:
                        time_gap_str = f"{int(delta_minutes // 1440)} 天"
                    elif delta_minutes > 60:
                        time_gap_str = f"{int(delta_minutes // 60)} 小时"
                    else:
                        time_gap_str = f"{int(delta_minutes)} 分钟"
                    
                    parts.append(
                        f"⚠️ 注意：距离上次任务已过去 {time_gap_str}。"
                        "过去的执行结果（如文件列表、网络状态）可能已失效，"
                        "如果涉及环境现状，请重新调用工具验证。"
                    )
            except Exception: pass

        for i, t in enumerate(turns, 1):
            prefix = f"[{time_gap_str}前] " if time_gap_str and i == 1 else ""
            line = f"  {i}. {prefix}用户: {t['user_input'][:80]}"
            if t.get("intent_summary"):
                line += f" | 意图: {t['intent_summary'][:40]}"
            parts.append(line)
            
            if t.get("steps"):
                steps = t["steps"]
                if len(steps) > HISTORY_STEP_LIMIT:
                    steps = steps[:3] + [{"type": "result", "content": "...(中间步骤省略)..."}] + steps[-3:]
                for step in steps:
                    if step["type"] == "call":
                        parts.append(f"     🔧 {step['tool']} (参数: {step['args']})")
                    elif step["type"] == "result":
                        parts.append(f"     ↳ {step['content']}")
            else:
                if t.get("tool"): parts.append(f"     🔧 {t['tool']}")
                if t.get("result"): parts.append(f"     ↳ {t['result'][:100]}")
            if t.get("reply"): parts.append(f"     答: {t['reply'][:100]}")

    if session and session.get("status") not in (None, "idle"):
        parts.append("\n[上一轮详情]")
        if session.get("last_result"): parts.append(f"结果: {session['last_result'][:200]}")
        artifacts = session.get("artifacts")
        if artifacts and isinstance(artifacts, str):
            try: artifacts = json.loads(artifacts)
            except Exception: pass
        if isinstance(artifacts, dict):
            sr = artifacts.get("search_results")
            if sr and isinstance(sr, list):
                parts.append("搜索结果:")
                for i, r in enumerate(sr[:2], 1):
                    parts.append(f"  {i}. {r.get('title', '?')[:30]} - {r.get('url', '')[:50]}")
                    c = (r.get("content", "") or "")[:50]
                    if c: parts.append(f"     {c}...")

    return "\n".join(parts)


def build_agent_context(store, user_input, focus_ctx, intent_summary, hint, keywords, base_system_prompt) -> tuple[str, set]:
    """
    核心工厂：组装最终的 System Content 和 已注入的 Skill 集合。
    """
    parts = []
    if focus_ctx: parts.append(focus_ctx)
    parts.append(f"用户意图参考：{intent_summary}")
    if keywords: parts.append(f"关键词：{', '.join(keywords)}")
    if hint == "high": parts.append("提示：这个任务可能比较复杂，建议先调用 plan_todos 规划。")
    parts.append("")

    injected_skill_ids = set()
    try:
        # 1. 正常检索普通记忆
        relevant = store.search(
            query=user_input,
            categories=["preference", "knowledge", "lesson", "command", "session_log"],
            top_k=MEMORY_TOP_K, min_score=MEMORY_MIN_SCORE,
        )
        
        # 2. 识别是否属于特定任务，动态强捞多个 Skill
        skill_queries = []
        lower_input = user_input.lower()
        
        # 遍历触发器，收集所有命中的查询
        for trigger_type, rule in SKILL_TRIGGER_MAP.items():
            if any(kw in lower_input for kw in rule["keywords"]):
                skill_queries.append(rule["query"])
                
        # 兜底：如果命中了打开网页的意图，但没抓到特定关键词，强捞全局底座
        if not skill_queries and any(w in lower_input for w in ["网页", "搜索", "点击", "打开"]):
            skill_queries.append("网页自动化与复杂交互 搜索与点击")

        # 对每个 query 执行检索
        skills = []
        for q in skill_queries:
            hits = store.search(
                query=q,
                categories=["skill"],
                top_k=1,
                min_score=SKILL_MIN_SCORE
            )
            if hits:
                skills.extend(hits)
                
        # 去重并注入到相关记忆列表中
        seen_ids = set()
        for s in skills:
            if s["id"] not in seen_ids:
                relevant.append(s)
                injected_skill_ids.add(s["id"])
                seen_ids.add(s["id"])
            
    except Exception as e:
        log_event("warning", f"记忆/技能检索失败: {e}", stage="memory")
        relevant = []

    if relevant:
        parts.append("[相关记忆与技能]")
        for r in relevant:
            cat = r.get("category", "?")
            content = (r.get("content") or "")
            score = r.get("final_score", r.get("score", 0))
            if cat in ("command", "skill"):
                parts.append(f"  [{cat} {score:.2f}]")
                for line in content.split("\n"): parts.append(f"    {line}")
            else:
                if len(content) > 200: content = content[:200] + "..."
                parts.append(f"  [{cat} {score:.2f}] {content}")
        parts.append("")

    parts.append(base_system_prompt)
    system_content = "\n".join(parts)
    
    return system_content, injected_skill_ids