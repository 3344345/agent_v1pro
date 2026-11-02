"""
MemoryStore 的 SQLite 实现。

从 V1 的 db.py 迁移，行为兼容。
"""

import os
import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager

from config import (
    DATA_DIR,
    HISTORY_RESULT_TRUNCATE, TURN_HISTORY_MAX,
    MEMORY_TOP_K, MEMORY_MIN_SCORE,
)
from logger import log_event
from core.memory.base import MemoryStore
from core.memory.schema import SCHEMA
from logger import log_event

DB_PATH = os.path.join(DATA_DIR, "agent.db")


class SqliteMemoryStore(MemoryStore):

    # ---------- 连接 ----------
    @contextmanager
    def _conn(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---------- 生命周期 ----------
    def init(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    # ---------- session ----------
    def clear_session(self) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM session")
            conn.execute("DELETE FROM turn_history")
            conn.execute("DELETE FROM task_summaries")
            conn.execute("""
                INSERT INTO session (id, status, updated_at)
                VALUES (1, 'idle', CURRENT_TIMESTAMP)
            """)

    def get_session(self) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM session WHERE id = 1"
            ).fetchone()
            return dict(row) if row else {}

    def update_session(self, **fields) -> None:
        if not fields:
            return

        allowed = {
            "session_id", "model_hash",
            "last_user_input", "last_intent",
            "last_tool", "last_tool_args", "last_result",
            "artifacts", "status", "parent_turn_id",
        }
        fields = {k: v for k, v in fields.items() if k in allowed}
        if not fields:
            return

        for k in ("last_tool_args", "artifacts"):
            if k in fields and isinstance(fields[k], (dict, list)):
                fields[k] = json.dumps(fields[k], ensure_ascii=False)

        fields["updated_at"] = datetime.now().isoformat(timespec="seconds")

        with self._conn() as conn:
            exists = conn.execute(
                "SELECT 1 FROM session WHERE id = 1"
            ).fetchone()
            if not exists:
                conn.execute("INSERT INTO session (id) VALUES (1)")

            cols = ", ".join(f"{k} = ?" for k in fields)
            vals = list(fields.values())
            conn.execute(f"UPDATE session SET {cols} WHERE id = 1", vals)

    # ---------- turn_history ----------
    def append_turn(self, user_input, intent_summary,
                    tool=None, tool_args=None, result=None,
                    status="done") -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO turn_history "
                "(user_input, intent_summary, tool, tool_args, result, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    user_input,
                    intent_summary,
                    tool,
                    json.dumps(tool_args, ensure_ascii=False) if tool_args else None,
                    (result or "")[:HISTORY_RESULT_TRUNCATE],
                    status,
                )
            )
            conn.execute(
                "DELETE FROM turn_history WHERE id NOT IN "
                "(SELECT id FROM turn_history ORDER BY id DESC LIMIT ?)",
                (TURN_HISTORY_MAX,)
            )

    def get_recent_turns(self, limit: int = 12,
                         only_unsummarized: bool = True) -> list:
        with self._conn() as conn:
            if only_unsummarized:
                cur = conn.execute(
                    "SELECT id, user_input, intent_summary, tool, tool_args, "
                    "       result, status, created_at "
                    "FROM turn_history WHERE summarized = 0 "
                    "ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
            else:
                cur = conn.execute(
                    "SELECT id, user_input, intent_summary, tool, tool_args, "
                    "       result, status, summarized, created_at "
                    "FROM turn_history "
                    "ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
            rows = cur.fetchall()
            return [dict(r) for r in reversed(rows)]

    # ---------- 上下文压缩 ----------
    def get_unsummarized_turns(self) -> list:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT id, user_input, intent_summary, tool, tool_args, "
                "       result, status, created_at "
                "FROM turn_history WHERE summarized = 0 ORDER BY id ASC"
            )
            return [dict(r) for r in cur.fetchall()]

    def mark_turns_summarized(self, turn_ids: list) -> None:
        if not turn_ids:
            return
        with self._conn() as conn:
            placeholders = ",".join("?" * len(turn_ids))
            conn.execute(
                f"UPDATE turn_history SET summarized = 1 "
                f"WHERE id IN ({placeholders})",
                turn_ids,
            )

    def save_summary(self, summary: str, covers_turn_ids: list,
                     session_id: str = None) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO task_summaries (session_id, summary, covers_turn_ids) "
                "VALUES (?, ?, ?)",
                (
                    session_id,
                    summary,
                    json.dumps(covers_turn_ids, ensure_ascii=False),
                )
            )
            return cur.lastrowid

    def get_summaries(self) -> list:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT id, summary, covers_turn_ids, created_at "
                "FROM task_summaries ORDER BY id ASC"
            )
            return [dict(r) for r in cur.fetchall()]

    # ---------- memories（含向量同步） ----------
    def save(self, category, content, source=None, trigger=None,
             inject=0, static=0, scope="global") -> int:
        """写 memories + 同步到向量库。返回 id。

        SQLite 是权威源；向量库失败不回滚（可后续重建）。
        """
        # 1. SQLite
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO memories "
                "(category, scope, content, source, trigger, inject, static) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (category, scope, content, source, trigger, inject, static)
            )
            mem_id = cur.lastrowid

        # 2. 同步向量库
        try:
            from core.memory.vector_store import get_vector_store
            vs = get_vector_store()
            vs.add(
                ids=[mem_id],
                contents=[content],
                metadatas=[{
                    "category": category,
                    "scope": scope,
                    "deprecated": 0,
                }],
            )
        except Exception as e:
            log_event("warning", f"向量库写入失败: {e}",
                      stage="memory", event="vector.save.error")

        return mem_id

    def search(self, query, categories=None, top_k=None,
               min_score=None) -> list:
        """语义检索。categories 可选。默认值从 config 读。"""
        top_k = top_k if top_k is not None else MEMORY_TOP_K
        min_score = min_score if min_score is not None else MEMORY_MIN_SCORE
        try:
            from core.memory.vector_store import get_vector_store
            vs = get_vector_store()
            where = ({"category": {"$in": list(categories)}}
                     if categories else None)
            hits = vs.search(query, top_k=top_k, where=where)
        except Exception as e:
            log_event("warning", f"向量检索失败: {e}",
                      stage="memory", event="vector.search.error")
            return []

        hits = [h for h in hits if h["score"] >= min_score]
        if not hits:
            return []

        ids = [h["id"] for h in hits]
        placeholders = ",".join("?" * len(ids))
        with self._conn() as conn:
            cur = conn.execute(
                f"SELECT id, category, scope, content, source, trigger, "
                f"       success_count, fail_count, weight, hit_count, "
                f"       created_at FROM memories "
                f"WHERE id IN ({placeholders}) AND deprecated = 0",
                ids
            )
            rows = {r["id"]: dict(r) for r in cur.fetchall()}

        result = []
        for h in hits:
            if h["id"] in rows:
                row = rows[h["id"]]
                row["score"] = round(h["score"], 3)
                
                # ================= P1 补丁：权重参与最终排序 =================
                w = row.get("weight", 1.0)
                row["final_score"] = round(row["score"] * w, 3)
                result.append(row)
        
        # 按照混合后的 final_score 从高到低重新排序
        result.sort(key=lambda x: x["final_score"], reverse=True)
        # ==========================================================

        # 命中计数（失败无害）
        if result:
            try:
                with self._conn() as conn:
                    for r in result:
                        conn.execute(
                            "UPDATE memories SET hit_count = hit_count + 1, "
                            "last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (r["id"],)
                        )
            except Exception:
                pass

        return result
    # ---------- memories 管理（供 memory_admin 使用） ----------
    def list_all(self, categories=None, limit=100) -> list:
        """列出记忆（只查 SQLite，不走向量）。"""
        sql = (
            "SELECT id, category, scope, content, source, trigger, "
            "       success_count, fail_count, weight, hit_count, "
            "       created_at, last_used_at "
            "FROM memories WHERE deprecated = 0"
        )
        params = []
        if categories:
            placeholders = ",".join("?" * len(categories))
            sql += f" AND category IN ({placeholders})"
            params.extend(categories)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def get(self, memory_id: int):
        """按 id 取单条（只查 SQLite）。"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ? AND deprecated = 0",
                (memory_id,),
            ).fetchone()
            return dict(row) if row else None

    def delete(self, memory_id: int) -> bool:
        """删除单条：SQLite 删，再删 Chroma 向量。"""
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM memories WHERE id = ?", (memory_id,)
            )
            deleted = cur.rowcount > 0

        if deleted:
            try:
                from core.memory.vector_store import get_vector_store
                get_vector_store().delete(ids=[memory_id])
            except Exception as e:
                log_event("warning",
                          f"Chroma 删除失败 id={memory_id}: {e}",
                          stage="memory", event="vector.delete.error")

        return deleted