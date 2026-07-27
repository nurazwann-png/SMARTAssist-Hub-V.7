"""
backend/user_memory.py
======================
Per-user persistent memory stored in PostgreSQL.

Remembers:
  preferred_lang    — "bm" | "en" (most recently used)
  preferred_agent   — most recently used agent key
  org_name          — organisation name extracted from queries / documents
  recent_topics     — rolling list of up to 10 recent query snippets
  doc_style_hints   — {agent_key: style note} for pre-filling context
  interaction_count — total interactions persisted

Usage:
    from backend.user_memory import load_memory, update_memory, add_topic, get_context_string
"""

from __future__ import annotations

import json
import re
import threading

from backend.db import get_conn, dict_cur

# ── Table bootstrap ───────────────────────────────────────────────────────────

_table_lock = threading.Lock()
_table_ready = False


def _ensure_table() -> None:
    global _table_ready
    if _table_ready:
        return
    with _table_lock:
        if _table_ready:
            return
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_memory (
                    email             TEXT PRIMARY KEY,
                    preferred_lang    TEXT    NOT NULL DEFAULT 'bm',
                    preferred_agent   TEXT    NOT NULL DEFAULT '',
                    org_name          TEXT    NOT NULL DEFAULT '',
                    recent_topics     JSONB   NOT NULL DEFAULT '[]'::jsonb,
                    doc_style_hints   JSONB   NOT NULL DEFAULT '{}'::jsonb,
                    interaction_count INTEGER NOT NULL DEFAULT 0,
                    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        _table_ready = True


# ── Core CRUD ─────────────────────────────────────────────────────────────────

_EMPTY: dict = {
    "preferred_lang": "bm",
    "preferred_agent": "",
    "org_name": "",
    "recent_topics": [],
    "doc_style_hints": {},
    "interaction_count": 0,
}


def load_memory(email: str) -> dict:
    """Return memory dict for *email*; returns safe defaults if user has no row yet."""
    if not email:
        return dict(_EMPTY)
    _ensure_table()
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute(
            "SELECT preferred_lang, preferred_agent, org_name, "
            "recent_topics, doc_style_hints, interaction_count "
            "FROM user_memory WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
    if row is None:
        return dict(_EMPTY)
    return dict(row)


def _upsert_row(email: str) -> None:
    """Ensure a row exists for *email* without overwriting anything."""
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute(
            "INSERT INTO user_memory (email) VALUES (%s) ON CONFLICT (email) DO NOTHING",
            (email,),
        )


def update_memory(email: str, **patch) -> None:
    """Partially update memory fields. Silently ignores unknown/empty values."""
    if not email:
        return
    _ensure_table()
    allowed = {"preferred_lang", "preferred_agent", "org_name", "doc_style_hints"}
    updates = {k: v for k, v in patch.items() if k in allowed and v}
    _upsert_row(email)
    if not updates:
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                "UPDATE user_memory SET interaction_count = interaction_count + 1, "
                "updated_at = NOW() WHERE email = %s",
                (email,),
            )
        return
    set_parts = [f"{k} = %s" for k in updates]
    set_parts += ["interaction_count = interaction_count + 1", "updated_at = NOW()"]
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute(
            f"UPDATE user_memory SET {', '.join(set_parts)} WHERE email = %s",
            list(updates.values()) + [email],
        )


def add_topic(email: str, topic: str) -> None:
    """Prepend *topic* to the rolling recent_topics list (max 10, deduplicated)."""
    if not email:
        return
    topic = topic.strip()[:120]
    if len(topic) < 8:
        return
    _ensure_table()
    _upsert_row(email)
    mem = load_memory(email)
    existing = mem.get("recent_topics") or []
    updated = [topic] + [t for t in existing if t != topic]
    updated = updated[:10]
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute(
            "UPDATE user_memory SET recent_topics = %s::jsonb, updated_at = NOW() "
            "WHERE email = %s",
            (json.dumps(updated, ensure_ascii=False), email),
        )


def set_doc_style_hint(email: str, agent_key: str, hint: str) -> None:
    """Store a style hint for a specific agent (e.g. letter format preference)."""
    if not email or not agent_key or not hint:
        return
    _ensure_table()
    _upsert_row(email)
    mem = load_memory(email)
    hints = dict(mem.get("doc_style_hints") or {})
    hints[agent_key] = hint[:200]
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute(
            "UPDATE user_memory SET doc_style_hints = %s::jsonb, updated_at = NOW() "
            "WHERE email = %s",
            (json.dumps(hints, ensure_ascii=False), email),
        )


# ── Org name extraction ───────────────────────────────────────────────────────

_ORG_RE = [
    re.compile(r'\b(SMK\s+[\w()]+(?:\s+[\w()]+){0,4})', re.IGNORECASE),
    re.compile(r'\b(SK\s+[\w()]+(?:\s+[\w()]+){0,4})', re.IGNORECASE),
    re.compile(r'\b(SJK(?:C|T)?\s+[\w()]+(?:\s+[\w()]+){0,4})', re.IGNORECASE),
    re.compile(r'\b(PPD\s+[\w]+(?:\s+[\w]+){0,3})', re.IGNORECASE),
    re.compile(r'\b(JPN\s+[\w]+(?:\s+[\w]+){0,2})', re.IGNORECASE),
    re.compile(r'\b(IAB\s+[\w]+(?:\s+[\w]+){0,2})', re.IGNORECASE),
    re.compile(r'sekolah\s+([\w()]+(?:\s+[\w()]+){0,4})', re.IGNORECASE),
]


def extract_org_name(text: str) -> str | None:
    """Return an organisation name found in *text*, or None."""
    for pattern in _ORG_RE:
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    return None


# ── Context string for injection into system prompts ─────────────────────────

def get_context_string(email: str, lang: str = "bm") -> str:
    """Return a formatted memory context block suitable for appending to a system prompt.

    Returns an empty string if there is nothing useful to inject.
    """
    if not email:
        return ""
    mem = load_memory(email)
    parts: list[str] = []
    en = lang == "en"

    if mem.get("org_name"):
        label = "User's organisation" if en else "Organisasi pengguna"
        parts.append(f"{label}: {mem['org_name']}")

    if mem.get("preferred_agent"):
        label = "Frequently used agent" if en else "Agen kerap digunakan"
        parts.append(f"{label}: {mem['preferred_agent']}")

    topics = (mem.get("recent_topics") or [])[:5]
    if topics:
        label = "Recent query topics" if en else "Topik soalan terkini"
        parts.append(f"{label}: {'; '.join(topics)}")

    hints = mem.get("doc_style_hints") or {}
    for agent_key, hint in list(hints.items())[:2]:
        label = f"Document style ({agent_key})" if en else f"Gaya dokumen ({agent_key})"
        parts.append(f"{label}: {hint}")

    if not parts:
        return ""

    header = (
        "\n\nUSER MEMORY (persistent across sessions — use this to personalise your response):"
        if en else
        "\n\nINGATAN PENGGUNA (kekal merentasi sesi — gunakan ini untuk memperibadikan respons anda):"
    )
    return header + "\n" + "\n".join(f"- {p}" for p in parts)
