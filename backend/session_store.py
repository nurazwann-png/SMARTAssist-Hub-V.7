"""
backend/session_store.py
========================
Penyimpanan sesi berterusan menggunakan SQLite.

Menggantikan dict dalam memori (_sessions) di app.py dan semua ejen supaya
data sesi kekal walaupun server dimulakan semula.

Skema ringkas — dua jadual:
  sessions   : metadata sesi (session_id, agent, title, created, updated, msg_count)
  kv_store   : simpanan nilai JSON serba-guna (session_id + namespace + key → JSON value)

Cara guna:
  from backend.session_store import SessionStore
  store = SessionStore()                       # singleton, selamat untuk thread

  # Chat history
  store.append_message(sid, {"role": "user", "content": "..."})
  msgs = store.get_messages(sid)

  # Namespace umum (ejen boleh simpan sebarang dict)
  store.set(sid, "letter", "phase", 2)
  val = store.get(sid, "letter", "phase")      # → 2
  store.set_all(sid, "letter", {...})          # ganti keseluruhan namespace
  data = store.get_all(sid, "letter")          # → dict semua kunci
  store.delete_ns(sid, "letter")               # padam semua kunci namespace

  # Metadata sesi
  store.upsert_meta(sid, agent="letter_generator", title="Surat PPD")
  metas = store.list_sessions(agent="letter_generator")
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

_DB_PATH = Path("data/sessions.db")
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    agent       TEXT DEFAULT '',
    title       TEXT DEFAULT '',
    created     TEXT NOT NULL,
    updated     TEXT NOT NULL,
    msg_count   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    meta_json   TEXT DEFAULT '{}',
    created     TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS kv_store (
    session_id  TEXT NOT NULL,
    namespace   TEXT NOT NULL,
    key         TEXT NOT NULL,
    value_json  TEXT NOT NULL,
    updated     TEXT NOT NULL,
    PRIMARY KEY (session_id, namespace, key)
);

CREATE INDEX IF NOT EXISTS idx_messages_sid ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_kv_sid_ns    ON kv_store(session_id, namespace);
"""


class SessionStore:
    """Thread-safe SQLite session store. Guna sebagai singleton."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._local = threading.local()
                    inst._init_db()
                    cls._instance = inst
        return cls._instance

    # ── Sambungan DB (satu per thread) ───────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        if not getattr(self._local, "conn", None):
            conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")   # tulis serentak lebih baik
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self):
        conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        conn.executescript(_SCHEMA)
        conn.commit()
        conn.close()

    def _now(self) -> str:
        return datetime.now().isoformat()

    # ── Metadata Sesi ────────────────────────────────────────────────────────

    def upsert_meta(self, session_id: str, agent: str = "", title: str = ""):
        conn = self._conn()
        now = self._now()
        conn.execute("""
            INSERT INTO sessions (session_id, agent, title, created, updated, msg_count)
            VALUES (?, ?, ?, ?, ?, 0)
            ON CONFLICT(session_id) DO UPDATE SET
                agent   = CASE WHEN excluded.agent != '' THEN excluded.agent ELSE agent END,
                title   = CASE WHEN excluded.title != '' THEN excluded.title ELSE title END,
                updated = excluded.updated
        """, (session_id, agent, title, now, now))
        conn.commit()

    def update_meta(self, session_id: str, **kwargs):
        """Kemaskini mana-mana medan metadata."""
        allowed = {"agent", "title", "updated", "msg_count"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        updates["updated"] = self._now()
        cols = ", ".join(f"{k} = ?" for k in updates)
        vals = list(updates.values()) + [session_id]
        self._conn().execute(f"UPDATE sessions SET {cols} WHERE session_id = ?", vals)
        self._conn().commit()

    def list_sessions(self, agent: str = "") -> list[dict]:
        q = "SELECT * FROM sessions"
        params: list = []
        if agent:
            q += " WHERE agent = ?"
            params.append(agent)
        q += " ORDER BY updated DESC"
        rows = self._conn().execute(q, params).fetchall()
        return [dict(r) for r in rows]

    def get_meta(self, session_id: str) -> dict | None:
        row = self._conn().execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None

    def session_exists(self, session_id: str) -> bool:
        row = self._conn().execute(
            "SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return row is not None

    # ── Mesej Chat ───────────────────────────────────────────────────────────

    def append_message(self, session_id: str, msg: dict):
        """Tambah satu mesej ke sejarah sesi."""
        self.upsert_meta(session_id)
        meta = {k: v for k, v in msg.items() if k not in ("role", "content")}
        self._conn().execute("""
            INSERT INTO messages (session_id, role, content, meta_json, created)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            msg.get("role", "user"),
            msg.get("content", ""),
            json.dumps(meta, ensure_ascii=False),
            self._now(),
        ))
        self._conn().execute("""
            UPDATE sessions SET msg_count = msg_count + 1, updated = ?
            WHERE session_id = ?
        """, (self._now(), session_id))
        self._conn().commit()

    def get_messages(self, session_id: str) -> list[dict]:
        """Kembalikan semua mesej sesi sebagai list dict."""
        rows = self._conn().execute(
            "SELECT role, content, meta_json FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,)
        ).fetchall()
        result = []
        for r in rows:
            msg = {"role": r["role"], "content": r["content"]}
            try:
                msg.update(json.loads(r["meta_json"] or "{}"))
            except (json.JSONDecodeError, ValueError):
                pass
            result.append(msg)
        return result

    def set_messages(self, session_id: str, messages: list[dict]):
        """Ganti keseluruhan sejarah mesej sesi."""
        conn = self._conn()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        self.upsert_meta(session_id)
        for msg in messages:
            meta = {k: v for k, v in msg.items() if k not in ("role", "content")}
            conn.execute("""
                INSERT INTO messages (session_id, role, content, meta_json, created)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                msg.get("role", "user"),
                msg.get("content", ""),
                json.dumps(meta, ensure_ascii=False),
                self._now(),
            ))
        conn.execute(
            "UPDATE sessions SET msg_count = ?, updated = ? WHERE session_id = ?",
            (len(messages), self._now(), session_id)
        )
        conn.commit()

    def clear_messages(self, session_id: str):
        self._conn().execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        self._conn().commit()

    # ── KV Store (namespace → key → value) ───────────────────────────────────

    def set(self, session_id: str, namespace: str, key: str, value):
        """Simpan satu nilai (apa-apa jenis yang boleh di-JSON-kan)."""
        self.upsert_meta(session_id)
        self._conn().execute("""
            INSERT INTO kv_store (session_id, namespace, key, value_json, updated)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id, namespace, key) DO UPDATE SET
                value_json = excluded.value_json,
                updated    = excluded.updated
        """, (session_id, namespace, key, json.dumps(value, ensure_ascii=False), self._now()))
        self._conn().commit()

    def get(self, session_id: str, namespace: str, key: str, default=None):
        """Ambil satu nilai. Kembalikan default jika tidak wujud."""
        row = self._conn().execute(
            "SELECT value_json FROM kv_store WHERE session_id=? AND namespace=? AND key=?",
            (session_id, namespace, key)
        ).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value_json"])
        except (json.JSONDecodeError, ValueError):
            return default

    def get_all(self, session_id: str, namespace: str) -> dict:
        """Kembalikan semua pasangan kunci-nilai dalam namespace sebagai dict."""
        rows = self._conn().execute(
            "SELECT key, value_json FROM kv_store WHERE session_id=? AND namespace=?",
            (session_id, namespace)
        ).fetchall()
        result = {}
        for r in rows:
            try:
                result[r["key"]] = json.loads(r["value_json"])
            except (json.JSONDecodeError, ValueError):
                result[r["key"]] = None
        return result

    def set_all(self, session_id: str, namespace: str, data: dict):
        """Ganti keseluruhan namespace dengan dict baharu."""
        conn = self._conn()
        self.upsert_meta(session_id)
        conn.execute(
            "DELETE FROM kv_store WHERE session_id=? AND namespace=?",
            (session_id, namespace)
        )
        now = self._now()
        for key, value in data.items():
            conn.execute("""
                INSERT INTO kv_store (session_id, namespace, key, value_json, updated)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, namespace, key, json.dumps(value, ensure_ascii=False), now))
        conn.commit()

    def delete_ns(self, session_id: str, namespace: str):
        """Padam semua kunci dalam namespace."""
        self._conn().execute(
            "DELETE FROM kv_store WHERE session_id=? AND namespace=?",
            (session_id, namespace)
        )
        self._conn().commit()

    def delete_key(self, session_id: str, namespace: str, key: str):
        self._conn().execute(
            "DELETE FROM kv_store WHERE session_id=? AND namespace=? AND key=?",
            (session_id, namespace, key)
        )
        self._conn().commit()

    # ── Pembersihan Sesi ─────────────────────────────────────────────────────

    def clear_session(self, session_id: str):
        """Padam semua data sesi (mesej + KV) tapi kekalkan metadata."""
        conn = self._conn()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM kv_store WHERE session_id = ?", (session_id,))
        conn.execute(
            "UPDATE sessions SET msg_count = 0, updated = ? WHERE session_id = ?",
            (self._now(), session_id)
        )
        conn.commit()

    def delete_session(self, session_id: str):
        """Padam sesi sepenuhnya termasuk metadata."""
        conn = self._conn()
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM kv_store WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()

    def prune_old_sessions(self, days: int = 30):
        """Padam sesi yang tidak aktif lebih dari N hari. Panggil dari startup."""
        conn = self._conn()
        cutoff = datetime.now().isoformat()[:10 - len(str(days))]
        # Guna pendekatan mudah: bandingkan string ISO date
        conn.execute("""
            DELETE FROM sessions WHERE updated < date('now', ?)
        """, (f"-{days} days",))
        conn.commit()


# Singleton global
_store = SessionStore()


def get_store() -> SessionStore:
    """Kembalikan singleton SessionStore."""
    return _store
