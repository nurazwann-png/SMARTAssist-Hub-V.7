"""
backend/doc_versions.py
=======================
Immutable document version history stored in PostgreSQL.

A new version is appended whenever letter_generator or report_generator
writes a final document string.  Callers only ever append or read.

Table: document_versions
  id             SERIAL PK
  session_id     TEXT
  agent          TEXT   -- 'letter_generator' | 'report_generator'
  version_number INTEGER (1-based, per session+agent)
  doc_type       TEXT   -- 'surat' | 'memo' | 'laporan' | ...
  fields         JSONB  -- snapshot of all collected fields at save time
  document_text  TEXT   -- the final plain-text document
  created_at     TIMESTAMPTZ
"""
from __future__ import annotations

import json
import threading
from datetime import datetime

from backend.db import get_conn, dict_cur

_lock        = threading.Lock()
_table_ready = False


def _ensure_table() -> None:
    global _table_ready
    if _table_ready:
        return
    with _lock:
        if _table_ready:
            return
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS document_versions (
                    id             SERIAL      PRIMARY KEY,
                    session_id     TEXT        NOT NULL,
                    agent          TEXT        NOT NULL,
                    version_number INTEGER     NOT NULL,
                    doc_type       TEXT        NOT NULL DEFAULT '',
                    fields         JSONB       NOT NULL DEFAULT '{}'::jsonb,
                    document_text  TEXT        NOT NULL,
                    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (session_id, agent, version_number)
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_doc_versions_lookup
                ON document_versions(session_id, agent, version_number DESC)
            """)
        _table_ready = True


def save_version(
    session_id: str,
    agent: str,
    document_text: str,
    doc_type: str = "",
    fields: dict | None = None,
) -> int:
    """Append a new version.  Returns the version_number assigned (1-based)."""
    if not document_text or not document_text.strip():
        return 0
    _ensure_table()
    fields_json = json.dumps(fields or {}, ensure_ascii=False)
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute("""
            SELECT COALESCE(MAX(version_number), 0) + 1
            FROM document_versions
            WHERE session_id = %s AND agent = %s
        """, (session_id, agent))
        next_v = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO document_versions
                (session_id, agent, version_number, doc_type, fields, document_text)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (session_id, agent, version_number) DO NOTHING
        """, (session_id, agent, next_v, doc_type, fields_json, document_text))
    return next_v


def list_versions(session_id: str, agent: str) -> list[dict]:
    """Return metadata for all versions (newest first) — no document_text."""
    _ensure_table()
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute("""
            SELECT id, version_number, doc_type, created_at
            FROM document_versions
            WHERE session_id = %s AND agent = %s
            ORDER BY version_number DESC
        """, (session_id, agent))
        rows = cur.fetchall()
    return [
        {
            "id":         r["id"],
            "version":    r["version_number"],
            "doc_type":   r["doc_type"],
            "created_at": _iso(r["created_at"]),
        }
        for r in rows
    ]


def get_version(version_id: int) -> dict | None:
    """Return a single version by primary key, including full document_text and fields."""
    _ensure_table()
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute("""
            SELECT id, session_id, agent, version_number, doc_type,
                   fields, document_text, created_at
            FROM document_versions
            WHERE id = %s
        """, (version_id,))
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id":            row["id"],
        "session_id":    row["session_id"],
        "agent":         row["agent"],
        "version":       row["version_number"],
        "doc_type":      row["doc_type"],
        "fields":        row["fields"],
        "document_text": row["document_text"],
        "created_at":    _iso(row["created_at"]),
    }


def _iso(v) -> str:
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)
