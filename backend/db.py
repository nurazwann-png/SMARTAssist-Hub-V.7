"""
backend/db.py
=============
Pool sambungan PostgreSQL bersama untuk semua modul backend.

Memerlukan pembolehubah persekitaran:
    DATABASE_URL=postgresql://user:password@localhost:5432/smartassist

Guna:
    from backend.db import get_conn

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1")
"""

import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

_DATABASE_URL = os.getenv("DATABASE_URL")

if not _DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL tidak ditetapkan.\n"
        "Tambah baris berikut dalam fail .env anda:\n"
        "  DATABASE_URL=postgresql://user:password@localhost:5432/smartassist"
    )

# Pool: min 2, max 20 sambungan serentak
_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=20,
            dsn=_DATABASE_URL,
        )
    return _pool


@contextmanager
def get_conn():
    """Context manager yang meminjam sambungan dari pool dan memulangkannya semula."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def dict_cur(conn):
    """Kembalikan cursor yang menghasilkan baris sebagai dict (RealDictCursor)."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
