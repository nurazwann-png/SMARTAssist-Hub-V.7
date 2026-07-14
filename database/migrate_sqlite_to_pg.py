"""
migrate_sqlite_to_pg.py
=======================
Pindahkan data sedia ada dari SQLite (data/sessions.db) ke PostgreSQL.

Cara guna:
    python database/migrate_sqlite_to_pg.py

Pastikan pembolehubah persekitaran ditetapkan dahulu (atau dalam .env):
    DATABASE_URL=postgresql://user:password@localhost:5432/smartassist
"""

import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = Path("data/sessions.db")
PG_URL = os.getenv("DATABASE_URL")


def sqlite_conn():
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def pg_conn():
    return psycopg2.connect(PG_URL)


def migrate():
    if not PG_URL:
        sys.exit("ERROR: DATABASE_URL tidak ditetapkan dalam .env")
    if not SQLITE_PATH.exists():
        sys.exit(f"ERROR: SQLite DB tidak dijumpai di {SQLITE_PATH}")

    src = sqlite_conn()
    dst = pg_conn()
    cur = dst.cursor()

    print("Memindahkan sessions...")
    rows = src.execute("SELECT * FROM sessions").fetchall()
    for r in rows:
        cur.execute("""
            INSERT INTO sessions (session_id, agent, title, msg_count, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO NOTHING
        """, (r["session_id"], r["agent"], r["title"], r["msg_count"],
              r["created"], r["updated"]))
    print(f"  {len(rows)} sesi dipindahkan.")

    print("Memindahkan messages...")
    rows = src.execute("SELECT * FROM messages ORDER BY id").fetchall()
    for r in rows:
        cur.execute("""
            INSERT INTO messages (session_id, role, content, meta, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (r["session_id"], r["role"], r["content"],
              json.dumps(json.loads(r["meta_json"] or "{}")), r["created"]))
    print(f"  {len(rows)} mesej dipindahkan.")

    print("Memindahkan kv_store...")
    rows = src.execute("SELECT * FROM kv_store").fetchall()
    for r in rows:
        try:
            value = json.loads(r["value_json"])
        except (json.JSONDecodeError, ValueError):
            value = None
        cur.execute("""
            INSERT INTO kv_store (session_id, namespace, key, value, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (session_id, namespace, key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
        """, (r["session_id"], r["namespace"], r["key"],
              json.dumps(value), r["updated"]))
    print(f"  {len(rows)} rekod kv_store dipindahkan.")

    dst.commit()
    src.close()
    dst.close()
    print("\nMigrasi selesai.")


if __name__ == "__main__":
    migrate()
