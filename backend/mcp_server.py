import os
import sqlite3
import math
import re
from collections import Counter
from pathlib import Path

_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "smartassist.db")
_conn = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_tables(_conn)
    return _conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students_staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ic_number TEXT,
            role TEXT NOT NULL,            -- 'student' or 'staff'
            school_code TEXT,
            school_name TEXT,
            district TEXT,
            state TEXT,
            category TEXT,
            status TEXT DEFAULT 'active',
            extra_json TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS kpm_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT,
            source_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS kpm_documents_fts
        USING fts5(title, content, category, content='kpm_documents', content_rowid='id');

        CREATE TRIGGER IF NOT EXISTS kpm_documents_ai AFTER INSERT ON kpm_documents BEGIN
            INSERT INTO kpm_documents_fts(rowid, title, content, category)
            VALUES (new.id, new.title, new.content, new.category);
        END;

        CREATE TRIGGER IF NOT EXISTS kpm_documents_ad AFTER DELETE ON kpm_documents BEGIN
            INSERT INTO kpm_documents_fts(kpm_documents_fts, rowid, title, content, category)
            VALUES ('delete', old.id, old.title, old.content, old.category);
        END;
    """)
    conn.commit()


# ── Record queries ──

def search_records(query: str, role: str | None = None, limit: int = 50) -> list[dict]:
    conn = _get_conn()
    clauses = ["1=1"]
    params: list = []

    if role:
        clauses.append("role = ?")
        params.append(role)

    keywords = query.strip().split()
    for kw in keywords:
        clauses.append("(name LIKE ? OR school_name LIKE ? OR district LIKE ?)")
        like = f"%{kw}%"
        params.extend([like, like, like])

    params.append(limit)
    rows = conn.execute(
        f"SELECT * FROM students_staff WHERE {' AND '.join(clauses)} LIMIT ?",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def insert_record(data: dict) -> int:
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO students_staff
           (name, ic_number, role, school_code, school_name, district, state, category, status, extra_json)
           VALUES (:name, :ic_number, :role, :school_code, :school_name, :district, :state, :category, :status, :extra_json)""",
        {
            "name": data["name"],
            "ic_number": data.get("ic_number"),
            "role": data["role"],
            "school_code": data.get("school_code"),
            "school_name": data.get("school_name"),
            "district": data.get("district"),
            "state": data.get("state"),
            "category": data.get("category"),
            "status": data.get("status", "active"),
            "extra_json": data.get("extra_json", "{}"),
        },
    )
    conn.commit()
    return cur.lastrowid


# ── Document queries (TF-IDF via FTS5) ──

def search_documents(query: str, top_k: int = 5) -> list[dict]:
    conn = _get_conn()
    tokens = _tokenize(query)
    if not tokens:
        return []

    fts_query = " OR ".join(tokens)
    rows = conn.execute(
        """SELECT d.id, d.title, d.content, d.category, d.source_file
           FROM kpm_documents d
           JOIN kpm_documents_fts f ON d.id = f.rowid
           WHERE kpm_documents_fts MATCH ?
           ORDER BY rank
           LIMIT ?""",
        (fts_query, top_k),
    ).fetchall()
    return [dict(r) for r in rows]


def search_documents_tfidf(query: str, top_k: int = 5) -> list[dict]:
    """Fallback TF-IDF search when FTS5 returns nothing or for richer ranking."""
    conn = _get_conn()
    all_docs = conn.execute(
        "SELECT id, title, content, category, source_file FROM kpm_documents"
    ).fetchall()
    if not all_docs:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    doc_count = len(all_docs)
    df: Counter = Counter()
    doc_tfs: list[tuple[dict, Counter]] = []

    for row in all_docs:
        d = dict(row)
        tokens = _tokenize(f"{d['title']} {d['content']}")
        tf = Counter(tokens)
        doc_tfs.append((d, tf))
        df.update(set(tokens))

    scored = []
    for d, tf in doc_tfs:
        total_tokens = sum(tf.values()) or 1
        score = 0.0
        for t in query_tokens:
            if df[t] == 0:
                continue
            tf_val = tf[t] / total_tokens
            idf_val = math.log((doc_count + 1) / (df[t] + 1)) + 1
            score += tf_val * idf_val
        if score > 0:
            scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:top_k]]


def insert_document(title: str, content: str, category: str = "", source_file: str = "") -> int:
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO kpm_documents (title, content, category, source_file) VALUES (?, ?, ?, ?)",
        (title, content, category, source_file),
    )
    conn.commit()
    return cur.lastrowid


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    stopwords = {"dan", "atau", "yang", "di", "ke", "dari", "untuk", "dengan", "ini", "itu",
                 "the", "and", "or", "is", "in", "of", "to", "for", "a", "an"}
    return [t for t in tokens if t not in stopwords and len(t) > 1]
