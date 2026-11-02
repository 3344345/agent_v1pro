"""
SQLite 表结构。所有 DDL 集中在这里。

表说明：
- session         : 单行表，当前会话状态
- turn_history    : 每轮流水，summarized 标记是否已被压缩
- task_summaries  : 压缩后的摘要
- memories        : preference/knowledge/lesson 统一表（批 8 实现）
- kv_state        : KV 快照引用（批 7 实现）
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS session (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    session_id TEXT,
    model_hash TEXT,
    last_user_input TEXT,
    last_intent TEXT,
    last_tool TEXT,
    last_tool_args TEXT,
    last_result TEXT,
    artifacts TEXT,
    status TEXT DEFAULT 'idle',
    parent_turn_id INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS turn_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    user_input TEXT,
    intent_summary TEXT,
    tool TEXT,
    tool_args TEXT,
    result TEXT,
    status TEXT DEFAULT 'done',
    summarized INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_turn_history_summarized
    ON turn_history(summarized, id);

CREATE TABLE IF NOT EXISTS task_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    summary TEXT NOT NULL,
    covers_turn_ids TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    scope TEXT DEFAULT 'global',
    content TEXT NOT NULL,
    source TEXT,
    trigger TEXT,
    inject INTEGER DEFAULT 0,
    static INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    weight REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    hit_count INTEGER DEFAULT 0,
    deprecated INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS kv_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    model_hash TEXT,
    file_path TEXT,
    token_count INTEGER,
    backend TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);
"""