"""
事件定义。

事件由 AgentRuntime 广播，前端通过 subscribe 订阅。
"""

import time
from dataclasses import dataclass, field


# ========== 事件类型常量 ==========
EVENT_USER_INPUT      = "user_input"
EVENT_STATE_CHANGED   = "state_changed"
EVENT_AGENT_STARTED   = "agent_started"
EVENT_ROUTE_DONE      = "route_done"
EVENT_TOOL_CALL       = "tool_call"
EVENT_TOOL_RESULT     = "tool_result"
EVENT_AGENT_FINISHED  = "agent_finished"
EVENT_MEMORY_COMPRESS = "memory_compress"
EVENT_ERROR           = "error"


@dataclass
class Event:
    """
    一个运行时事件。

    type    : 事件类型，用上面的 EVENT_* 常量
    payload : 事件相关数据，dict 结构，字段因事件类型而异
    ts      : 时间戳（秒，float）
    """
    type: str
    payload: dict = field(default_factory=dict)
    ts: float = field(default_factory=time.time)