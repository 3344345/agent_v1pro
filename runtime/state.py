"""
Agent 状态枚举。

状态机：
    IDLE → PREPARING → RUNNING → DONE → IDLE
                          ↓
                     CANCELLED → IDLE
                          ↓
                       ERROR → IDLE

PREPARING = 压缩 + 路由 + 读记忆 + 拼 prompt（准备阶段）
RUNNING   = 执行任务（可能调工具、可能调 plan_todos，由模型决定）
"""

from enum import Enum


class AgentState(str, Enum):
    IDLE      = "idle"
    PREPARING = "preparing"
    RUNNING   = "running"
    DONE      = "done"
    CANCELLED = "cancelled"
    ERROR     = "error"


# 合法状态转移表：{当前状态: [可达状态]}
TRANSITIONS = {
    AgentState.IDLE:      [AgentState.PREPARING, AgentState.ERROR],
    AgentState.PREPARING: [AgentState.RUNNING, AgentState.CANCELLED, AgentState.ERROR],
    AgentState.RUNNING:   [AgentState.DONE, AgentState.CANCELLED, AgentState.ERROR],
    AgentState.DONE:      [AgentState.IDLE],
    AgentState.CANCELLED: [AgentState.IDLE],
    AgentState.ERROR:     [AgentState.IDLE],
}


def can_transition(from_state: AgentState, to_state: AgentState) -> bool:
    """检查状态转移是否合法"""
    return to_state in TRANSITIONS.get(from_state, [])