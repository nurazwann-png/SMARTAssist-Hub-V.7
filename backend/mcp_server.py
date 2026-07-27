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
                 "the", "and", "or", "is", "in", "of", "to", "for", "a", "an", "ia",
                 "pada", "oleh", "jika", "bagi", "telah", "akan", "tidak", "ada"}
    return [t for t in tokens if t not in stopwords and len(t) > 1]


# ── KPM term expansions (abbreviation → full terms added to query) ────────────
_KPM_EXPANSIONS: dict[str, list[str]] = {
    "emis":   ["sistem maklumat", "sekolah", "pendaftaran"],
    "delima": ["digital", "pembelajaran", "google", "microsoft"],
    "apdm":   ["kehadiran", "murid", "pelajar"],
    "dtpcare":["guru", "kakitangan", "perkhidmatan"],
    "skas":   ["sekolah", "akaun", "kewangan"],
    "sso":    ["single sign on", "log masuk"],
    "kpm":    ["kementerian pendidikan malaysia"],
    "ppd":    ["pejabat pendidikan daerah"],
    "jpn":    ["jabatan pendidikan negeri"],
    "bpsh":   ["bahagian pengurusan sekolah harian"],
    "spm":    ["sijil pelajaran malaysia", "peperiksaan"],
    "upsr":   ["ujian pencapaian sekolah rendah"],
    "pt3":    ["pentaksiran tingkatan tiga"],
}


def _expand_query(query: str) -> str:
    """Add KPM domain abbreviations to the query to improve recall."""
    low = query.lower()
    extras: list[str] = []
    for abbr, expansions in _KPM_EXPANSIONS.items():
        if abbr in low.split() or f" {abbr}" in low:
            extras.extend(expansions)
    if extras:
        return query + " " + " ".join(extras)
    return query


def _best_passage(content: str, query_tokens: list[str], window: int = 600) -> str:
    """Return the most relevant ~600-char passage from *content*.

    Splits content by paragraph, scores each paragraph by token overlap
    with the query, and returns the best one (truncated to *window* chars).
    Falls back to the first *window* chars if nothing scores.
    """
    paragraphs = [p.strip() for p in re.split(r"\n{2,}|\. {2,}", content) if p.strip()]
    if not paragraphs:
        return content[:window]

    best_para, best_score = "", 0
    for para in paragraphs:
        para_tokens = set(_tokenize(para))
        score = sum(1 for t in query_tokens if t in para_tokens)
        if score > best_score:
            best_score, best_para = score, para

    passage = (best_para or paragraphs[0])[:window]
    if len(best_para) > window:
        passage += "..."
    return passage


def search_documents_hybrid(query: str, top_k: int = 5) -> list[dict]:
    """Hybrid retrieval: FTS5 + TF-IDF, deduped and title-boosted.

    Steps:
    1. Expand the query with KPM domain abbreviations
    2. FTS5 BM25 search (primary)
    3. TF-IDF search (complementary — fills gaps FTS5 misses)
    4. Deduplicate by doc id, boost score if query tokens appear in title
    5. Extract the most relevant passage per doc instead of raw prefix
    6. Return top_k docs with relevance_score for confidence estimation
    """
    expanded = _expand_query(query)
    query_tokens = _tokenize(expanded)

    # Gather candidates from both sources
    fts_docs  = search_documents(expanded, top_k=top_k + 3)
    tfidf_docs = search_documents_tfidf(expanded, top_k=top_k + 3)

    # Merge, deduplicate, and score
    seen: dict[int, dict] = {}
    for rank, doc in enumerate(fts_docs):
        doc_id = doc["id"]
        seen[doc_id] = {**doc, "_score": top_k + 3 - rank}

    for rank, doc in enumerate(tfidf_docs):
        doc_id = doc["id"]
        if doc_id not in seen:
            seen[doc_id] = {**doc, "_score": (top_k + 3 - rank) * 0.7}
        else:
            seen[doc_id]["_score"] += (top_k + 3 - rank) * 0.5  # bonus for appearing in both

    # Title boost: +3 for each query token found in the title
    for doc in seen.values():
        title_tokens = set(_tokenize(doc.get("title", "")))
        boost = sum(1 for t in query_tokens if t in title_tokens)
        doc["_score"] += boost * 3

    ranked = sorted(seen.values(), key=lambda d: d["_score"], reverse=True)[:top_k]

    # Replace raw content with best passage + attach relevance label
    max_score = ranked[0]["_score"] if ranked else 1
    for doc in ranked:
        doc["passage"] = _best_passage(doc["content"], query_tokens)
        score_ratio = doc["_score"] / max(max_score, 1)
        doc["relevance"] = "high" if score_ratio >= 0.7 else ("medium" if score_ratio >= 0.4 else "low")

    return ranked
