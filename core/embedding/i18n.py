# core/i18n.py
from config import AGENT_LANG

TEXTS = {
    "zh": {
        "welcome": "输入 exit / quit 退出；任务执行中输入 stop 停止\n",
        "exit_summary": "正在总结本次会话，请稍候...",
        "bye": "再见！",
        "stopping": "⏹️  已发出停止信号，< 5 秒内停",
        "stop_rejected": "⚠️  停止请求未被接受",
        "task_running": "⚠️  任务正在运行，输入 'stop' 停止",
        "task_failed": "\n❌ 任务未能完成（可能是后端模型失联或连续空响应），请检查 logs/llama-server.log\n",
        "agent_prefix": "Agent：",
        "reflecting": "🤔 [反思] 正在评估任务经验...",
        "reflect_skip": "✅ [反思] 完成：本次任务没有需要长期记忆的内容。",
        "reflect_saved": "🧠 [反思] 已存入长期记忆！",
        "reflect_cat": "   类别: {}",
        "reflect_drop_len": "🚫 [反思] 记忆超长（>{}字），已丢弃。",
        "reflect_drop_code": "🚫 [反思] 记忆包含代码块，已丢弃。",
        "reflect_drop_causal": "🚫 [反思] 包含因果臆断词，已丢弃。",
        "reflect_drop_pref": "🚫 [反思] 偏好记忆已在配置中禁用，本次记录作废。",
    },
    "en": {
        "welcome": "Type exit / quit to leave; type stop during a task to interrupt.\n",
        "exit_summary": "Summarizing this session, please wait...",
        "bye": "Goodbye!",
        "stopping": "⏹️  Stop signal sent, stopping in <5s",
        "stop_rejected": "⚠️  Stop request rejected",
        "task_running": "⚠️  Task is running, type 'stop' to stop",
        "task_failed": "\n❌ Task failed (model offline or empty response), check logs/llama-server.log\n",
        "agent_prefix": "Agent: ",
        "reflecting": "🤔 [Reflect] Evaluating task experience...",
        "reflect_skip": "✅ [Reflect] Done: no long-term memory needed.",
        "reflect_saved": "🧠 [Reflect] Saved to long-term memory!",
        "reflect_cat": "   Category: {}",
        "reflect_drop_len": "🚫 [Reflect] Memory too long (>{ } chars), dropped.",
        "reflect_drop_code": "🚫 [Reflect] Memory contains code blocks, dropped.",
        "reflect_drop_causal": "🚫 [Reflect] Memory contains causal assumptions, dropped.",
        "reflect_drop_pref": "🚫 [Reflect] Preference memory disabled, dropped.",
    }
}

def t(key: str, *args) -> str:
    lang_dict = TEXTS.get(AGENT_LANG, TEXTS["zh"])
    template = lang_dict.get(key, TEXTS["zh"].get(key, key))
    if args:
        return template.format(*args)
    return template