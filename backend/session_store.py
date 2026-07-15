"""
backend/session_store.py
========================
Penyimpanan sesi berterusan menggunakan PostgreSQL.

API awam tidak berubah — app.py dan semua ejen boleh terus guna tanpa sebarang
perubahan. Hanya bahagian dalaman (SQLite → psycopg2) yang bertukar.

Cara guna (sama seperti sebelum):
    from backend.session_store import SessionStore
    store = SessionStore()

    store.append_message(sid, {"role": "user", "content": "..."})
    msgs = store.get_messages(sid)

    store.set(sid, "letter", "phase", 2)
    val = store.get(sid, "letter", "phase")
    store.set_all(sid, "letter", {...})
    data = store.get_all(sid, "letter")
    store.delete_ns(sid, "letter")

    store.upsert_meta(sid, agent="letter_generator", title="Surat PPD")
    metas = store.list_sessions(agent="letter_generator")
"""

import json
import threading
from datetime import datetime, timezone


def _serial(row: dict) -> dict:
    """Convert datetime values to ISO strings for JSON serialisation."""
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()}

import psycopg2.extras

from backend.db import dict_cur, get_conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionStore:
    """Thread-safe PostgreSQL session store. Guna sebagai singleton."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    cls._instance = inst
        return cls._instance

    # ── Metadata Sesi ────────────────────────────────────────────────────────

    def upsert_meta(self, session_id: str, agent: str = "", title: str = ""):
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute("""
                INSERT INTO sessions (session_id, agent, title, msg_count, created_at, updated_at)
                VALUES (%s, %s, %s, 0, NOW(), NOW())
                ON CONFLICT (session_id) DO UPDATE SET
                    agent      = CASE WHEN EXCLUDED.agent != '' THEN EXCLUDED.agent ELSE sessions.agent END,
                    title      = CASE WHEN EXCLUDED.title != '' THEN EXCLUDED.title ELSE sessions.title END,
                    updated_at = NOW()
            """, (session_id, agent, title))

    def update_meta(self, session_id: str, **kwargs):
        allowed = {"agent", "title", "msg_count"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        # Bina SET secara dinamik
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        set_clause += ", updated_at = NOW()"
        vals = list(updates.values()) + [session_id]
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                f"UPDATE sessions SET {set_clause} WHERE session_id = %s", vals
            )

    def list_sessions(self, agent: str = "") -> list[dict]:
        with get_conn() as conn, dict_cur(conn) as cur:
            if agent:
                cur.execute(
                    "SELECT session_id, agent, title, msg_count, "
                    "created_at AS created, updated_at AS updated "
                    "FROM sessions WHERE agent = %s ORDER BY updated_at DESC",
                    (agent,)
                )
            else:
                cur.execute(
                    "SELECT session_id, agent, title, msg_count, "
                    "created_at AS created, updated_at AS updated "
                    "FROM sessions ORDER BY updated_at DESC"
                )
            return [_serial(dict(r)) for r in cur.fetchall()]

    def get_meta(self, session_id: str) -> dict | None:
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                "SELECT session_id, agent, title, msg_count, "
                "created_at AS created, updated_at AS updated "
                "FROM sessions WHERE session_id = %s",
                (session_id,)
            )
            row = cur.fetchone()
            return _serial(dict(row)) if row else None

    def session_exists(self, session_id: str) -> bool:
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                "SELECT 1 FROM sessions WHERE session_id = %s", (session_id,)
            )
            return cur.fetchone() is not None

    # ── Mesej Chat ───────────────────────────────────────────────────────────

    def append_message(self, session_id: str, msg: dict):
        self.upsert_meta(session_id)
        meta = {k: v for k, v in msg.items() if k not in ("role", "content")}
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute("""
                INSERT INTO messages (session_id, role, content, meta, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (
                session_id,
                msg.get("role", "user"),
                msg.get("content", ""),
                json.dumps(meta, ensure_ascii=False),
            ))
            cur.execute("""
                UPDATE sessions
                SET msg_count = msg_count + 1, updated_at = NOW()
                WHERE session_id = %s
            """, (session_id,))

    def get_messages(self, session_id: str) -> list[dict]:
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                "SELECT role, content, meta FROM messages "
                "WHERE session_id = %s ORDER BY id",
                (session_id,)
            )
            result = []
            for r in cur.fetchall():
                msg = {"role": r["role"], "content": r["content"]}
                try:
                    extra = r["meta"]
                    if isinstance(extra, str):
                        extra = json.loads(extra)
                    if isinstance(extra, dict):
                        msg.update(extra)
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
                result.append(msg)
            return result

    def set_messages(self, session_id: str, messages: list[dict]):
        self.upsert_meta(session_id)
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
            for msg in messages:
                meta = {k: v for k, v in msg.items() if k not in ("role", "content")}
                cur.execute("""
                    INSERT INTO messages (session_id, role, content, meta, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (
                    session_id,
                    msg.get("role", "user"),
                    msg.get("content", ""),
                    json.dumps(meta, ensure_ascii=False),
                ))
            cur.execute(
                "UPDATE sessions SET msg_count = %s, updated_at = NOW() WHERE session_id = %s",
                (len(messages), session_id)
            )

    def clear_messages(self, session_id: str):
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))

    # ── KV Store (namespace → key → value) ───────────────────────────────────

    def set(self, session_id: str, namespace: str, key: str, value):
        self.upsert_meta(session_id)
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute("""
                INSERT INTO kv_store (session_id, namespace, key, value, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (session_id, namespace, key) DO UPDATE SET
                    value      = EXCLUDED.value,
                    updated_at = NOW()
            """, (session_id, namespace, key, json.dumps(value, ensure_ascii=False)))

    def get(self, session_id: str, namespace: str, key: str, default=None):
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                "SELECT value FROM kv_store WHERE session_id=%s AND namespace=%s AND key=%s",
                (session_id, namespace, key)
            )
            row = cur.fetchone()
        if row is None:
            return default
        # psycopg2 auto-deserialises JSONB — return as-is
        return row["value"]

    def get_all(self, session_id: str, namespace: str) -> dict:
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                "SELECT key, value FROM kv_store WHERE session_id=%s AND namespace=%s",
                (session_id, namespace)
            )
            # psycopg2 auto-deserialises JSONB — return as-is
            return {r["key"]: r["value"] for r in cur.fetchall()}

    def set_all(self, session_id: str, namespace: str, data: dict):
        self.upsert_meta(session_id)
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                "DELETE FROM kv_store WHERE session_id=%s AND namespace=%s",
                (session_id, namespace)
            )
            for key, value in data.items():
                cur.execute("""
                    INSERT INTO kv_store (session_id, namespace, key, value, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (session_id, namespace, key, json.dumps(value, ensure_ascii=False)))

    def delete_ns(self, session_id: str, namespace: str):
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                "DELETE FROM kv_store WHERE session_id=%s AND namespace=%s",
                (session_id, namespace)
            )

    def delete_key(self, session_id: str, namespace: str, key: str):
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                "DELETE FROM kv_store WHERE session_id=%s AND namespace=%s AND key=%s",
                (session_id, namespace, key)
            )

    # ── Pembersihan Sesi ─────────────────────────────────────────────────────

    def clear_session(self, session_id: str):
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
            cur.execute("DELETE FROM kv_store WHERE session_id = %s", (session_id,))
            cur.execute(
                "UPDATE sessions SET msg_count = 0, updated_at = NOW() WHERE session_id = %s",
                (session_id,)
            )

    def delete_session(self, session_id: str):
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
            cur.execute("DELETE FROM kv_store WHERE session_id = %s", (session_id,))
            cur.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))

    def prune_old_sessions(self, days: int = 30):
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                "DELETE FROM sessions WHERE updated_at < NOW() - INTERVAL '%s days'",
                (days,)
            )


# Singleton global
_store = SessionStore()


def get_store() -> SessionStore:
    return _store
