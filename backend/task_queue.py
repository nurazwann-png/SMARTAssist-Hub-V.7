"""Background task queue backed by PostgreSQL.

Tasks are stored in the `bg_tasks` table.  A single daemon thread
(`_worker`) polls for PENDING tasks, executes them, and stores
the result.  The SSE endpoint `/api/tasks/stream/{task_id}` lets
the frontend poll until the task is DONE or FAILED.

Supported task types:
  - "agent_call"  — call any agent's handle() with arbitrary kwargs
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# ── States ─────────────────────────────────────────────────────────────────────
PENDING  = "PENDING"
RUNNING  = "RUNNING"
DONE     = "DONE"
FAILED   = "FAILED"

# ── Polling interval for the worker thread ──────────────────────────────────────
_POLL_INTERVAL = 2  # seconds


# ── DB helpers ──────────────────────────────────────────────────────────────────

def _db():
    """Return the get_conn context manager from backend.db."""
    from backend.db import get_conn
    return get_conn


def _ensure_table():
    with _db()() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bg_tasks (
                    id           TEXT PRIMARY KEY,
                    session_id   TEXT NOT NULL,
                    user_email   TEXT NOT NULL DEFAULT '',
                    task_type    TEXT NOT NULL,
                    payload      JSONB NOT NULL DEFAULT '{}',
                    status       TEXT NOT NULL DEFAULT 'PENDING',
                    progress     TEXT NOT NULL DEFAULT '',
                    result       JSONB,
                    error        TEXT,
                    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_bg_tasks_session
                ON bg_tasks (session_id, status)
            """)


# ── Public API ──────────────────────────────────────────────────────────────────

def enqueue(
    task_type: str,
    payload: dict,
    session_id: str = "default",
    user_email: str = "",
) -> str:
    """Insert a new task and return its id."""
    _ensure_table()
    task_id = str(uuid.uuid4())
    with _db()() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO bg_tasks (id, session_id, user_email, task_type, payload)
                   VALUES (%s, %s, %s, %s, %s)""",
                (task_id, session_id, user_email, task_type, json.dumps(payload)),
            )
    logger.info("[TaskQueue] Enqueued %s task %s for session %s", task_type, task_id, session_id)
    return task_id


def get_task(task_id: str) -> dict | None:
    """Return the full task row as a dict, or None."""
    _ensure_table()
    with _db()() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, session_id, task_type, status, progress, result, error, created_at, updated_at "
                "FROM bg_tasks WHERE id = %s",
                (task_id,),
            )
            row = cur.fetchone()
    if not row:
        return None
    cols = ["id", "session_id", "task_type", "status", "progress", "result", "error", "created_at", "updated_at"]
    return dict(zip(cols, row))


def list_tasks(session_id: str) -> list[dict]:
    """Return all tasks for a session, newest first."""
    _ensure_table()
    with _db()() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, task_type, status, progress, created_at FROM bg_tasks "
                "WHERE session_id = %s ORDER BY created_at DESC LIMIT 50",
                (session_id,),
            )
            rows = cur.fetchall()
    cols = ["id", "task_type", "status", "progress", "created_at"]
    return [dict(zip(cols, r)) for r in rows]


def _update_task(task_id: str, **kwargs):
    """Update mutable fields on a task row."""
    allowed = {"status", "progress", "result", "error"}
    sets = {k: v for k, v in kwargs.items() if k in allowed}
    if not sets:
        return
    parts = ", ".join(f"{k} = %s" for k in sets)
    vals = list(sets.values()) + [task_id]
    with _db()() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE bg_tasks SET {parts}, updated_at = NOW() WHERE id = %s",
                vals,
            )


# ── Task executor ───────────────────────────────────────────────────────────────

def _execute_agent_call(task_id: str, payload: dict):
    """Execute an agent_call task payload.

    Expected payload keys:
        agent        — agent module name (e.g. "report_generator")
        query        — user message string
        session_id   — session id
        lang         — "bm" | "en"
        user_name    — optional
        user_context — optional
        history      — optional list of prior messages
    """
    import inspect
    from agents import (
        data_analysis, letter_generator, kpm_support,
        report_generator, document_reviewer,
    )
    agent_map = {
        "data_analysis":     data_analysis,
        "letter_generator":  letter_generator,
        "kpm_support":       kpm_support,
        "report_generator":  report_generator,
        "document_reviewer": document_reviewer,
    }
    agent = payload.get("agent", "")
    module = agent_map.get(agent)
    if not module or not hasattr(module, "handle"):
        raise ValueError(f"Unknown agent: {agent}")

    _update_task(task_id, progress=f"Menjalankan agen {agent}…")

    sig = inspect.signature(module.handle)
    kwargs: dict[str, Any] = {"query": payload.get("query", "")}
    if "history"      in sig.parameters: kwargs["history"]      = payload.get("history", [])
    if "session_id"   in sig.parameters: kwargs["session_id"]   = payload.get("session_id", "default")
    if "lang"         in sig.parameters: kwargs["lang"]         = payload.get("lang", "bm")
    if "user_name"    in sig.parameters: kwargs["user_name"]    = payload.get("user_name", "")
    if "user_context" in sig.parameters: kwargs["user_context"] = payload.get("user_context", "")

    output = module.handle(**kwargs)

    # Persist the message to session history
    session_id = payload.get("session_id", "default")
    try:
        from backend.session_store import get_store
        get_store().append_message(session_id, {"role": "assistant", "content": output, "agent": agent})
    except Exception:
        pass

    return {"output": output, "agent": agent}


_EXECUTORS = {
    "agent_call": _execute_agent_call,
}


def _process_one(row: dict):
    task_id   = row["id"]
    task_type = row["task_type"]
    payload   = row["payload"] or {}

    _update_task(task_id, status=RUNNING, progress="Memulakan tugas…")
    try:
        executor = _EXECUTORS.get(task_type)
        if not executor:
            raise ValueError(f"Unknown task_type: {task_type}")
        result = executor(task_id, payload)
        _update_task(task_id, status=DONE, progress="Selesai.", result=json.dumps(result))
        logger.info("[TaskQueue] Task %s DONE", task_id)
    except Exception as exc:
        logger.exception("[TaskQueue] Task %s FAILED: %s", task_id, exc)
        _update_task(task_id, status=FAILED, progress="Gagal.", error=str(exc))


# ── Worker thread ───────────────────────────────────────────────────────────────

_worker_started = False
_worker_lock    = threading.Lock()


def _worker_loop():
    """Daemon thread: poll for PENDING tasks and execute them one at a time."""
    _ensure_table()
    while True:
        try:
            with _db()() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE bg_tasks SET status = %s "
                        "WHERE id = (SELECT id FROM bg_tasks WHERE status = %s "
                        "ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED) "
                        "RETURNING id, task_type, payload",
                        (RUNNING, PENDING),
                    )
                    row = cur.fetchone()
                    conn.commit()
            if row:
                task = {"id": row[0], "task_type": row[1], "payload": row[2]}
                _process_one(task)
        except Exception:
            logger.exception("[TaskQueue] Worker loop error")
        time.sleep(_POLL_INTERVAL)


def start_worker():
    """Start the background worker thread (idempotent)."""
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        t = threading.Thread(target=_worker_loop, daemon=True, name="TaskQueueWorker")
        t.start()
        _worker_started = True
        logger.info("[TaskQueue] Worker thread started")
