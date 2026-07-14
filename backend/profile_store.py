"""User profile storage — saves per-user profile data in the same SQLite DB."""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

_DB_PATH = Path("data/sessions.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_profiles (
    google_sub  TEXT PRIMARY KEY,
    email       TEXT NOT NULL,
    nama        TEXT DEFAULT '',
    jawatan     TEXT DEFAULT '',
    stesen      TEXT DEFAULT '',
    daerah      TEXT DEFAULT '',
    negeri      TEXT DEFAULT '',
    updated     TEXT NOT NULL
);
"""

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init():
    with _lock:
        c = _conn()
        c.executescript(_SCHEMA)
        c.commit()
        c.close()


_init()


def get_profile(google_sub: str) -> dict:
    c = _conn()
    row = c.execute(
        "SELECT * FROM user_profiles WHERE google_sub = ?", (google_sub,)
    ).fetchone()
    c.close()
    return dict(row) if row else {}


def save_profile(google_sub: str, email: str, data: dict) -> dict:
    allowed = {"nama", "jawatan", "stesen", "daerah", "negeri"}
    fields = {k: v for k, v in data.items() if k in allowed}
    now = datetime.now().isoformat()
    with _lock:
        c = _conn()
        c.execute("""
            INSERT INTO user_profiles (google_sub, email, nama, jawatan, stesen, daerah, negeri, updated)
            VALUES (:sub, :email, :nama, :jawatan, :stesen, :daerah, :negeri, :now)
            ON CONFLICT(google_sub) DO UPDATE SET
                email   = excluded.email,
                nama    = CASE WHEN :nama    != '' THEN :nama    ELSE nama    END,
                jawatan = CASE WHEN :jawatan != '' THEN :jawatan ELSE jawatan END,
                stesen  = CASE WHEN :stesen  != '' THEN :stesen  ELSE stesen  END,
                daerah  = CASE WHEN :daerah  != '' THEN :daerah  ELSE daerah  END,
                negeri  = CASE WHEN :negeri  != '' THEN :negeri  ELSE negeri  END,
                updated = excluded.updated
        """, {
            "sub": google_sub, "email": email,
            "nama": fields.get("nama", ""),
            "jawatan": fields.get("jawatan", ""),
            "stesen": fields.get("stesen", ""),
            "daerah": fields.get("daerah", ""),
            "negeri": fields.get("negeri", ""),
            "now": now,
        })
        c.commit()
        row = c.execute(
            "SELECT * FROM user_profiles WHERE google_sub = ?", (google_sub,)
        ).fetchone()
        c.close()
    return dict(row) if row else {}
