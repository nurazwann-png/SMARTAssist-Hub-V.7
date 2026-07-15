"""Letterhead store — manages uploaded letterhead/logo images via PostgreSQL.

API awam tidak berubah. Fail fizikal masih disimpan di static/letterheads/;
hanya metadata yang kini disimpan dalam PostgreSQL.
"""

import uuid
from pathlib import Path

from backend.db import dict_cur, get_conn

_BASE = Path(__file__).parent.parent
_LH_DIR = _BASE / "static" / "letterheads"

_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
TYPES = ("letterhead", "logo")


def _serial(row: dict) -> dict:
    """Convert datetime values to ISO strings so JSONResponse can serialise them."""
    from datetime import datetime
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()}


def _ensure_dir():
    _LH_DIR.mkdir(parents=True, exist_ok=True)


def _active_col(lh_type: str) -> str:
    return "active_logo_id" if lh_type == "logo" else "active_letterhead_id"


# ── Baca ─────────────────────────────────────────────────────────────────────

def list_letterheads(lh_type: str | None = None) -> list[dict]:
    with get_conn() as conn, dict_cur(conn) as cur:
        if lh_type:
            cur.execute(
                "SELECT id, name, filename, original_name, type, is_active, "
                "uploaded_at AS uploaded FROM letterheads WHERE type = %s "
                "ORDER BY uploaded_at DESC",
                (lh_type,)
            )
        else:
            cur.execute(
                "SELECT id, name, filename, original_name, type, is_active, "
                "uploaded_at AS uploaded FROM letterheads ORDER BY uploaded_at DESC"
            )
        return [_serial(dict(r)) for r in cur.fetchall()]


def get_active_by_type(lh_type: str) -> dict | None:
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute(
            "SELECT id, name, filename, original_name, type, is_active, "
            "uploaded_at AS uploaded FROM letterheads "
            "WHERE type = %s AND is_active = TRUE LIMIT 1",
            (lh_type,)
        )
        row = cur.fetchone()
    if not row:
        return None
    entry = _serial(dict(row))
    if not (_LH_DIR / entry["filename"]).exists():
        return None
    return entry


def get_active_path_by_type(lh_type: str) -> Path | None:
    lh = get_active_by_type(lh_type)
    if not lh:
        return None
    p = _LH_DIR / lh["filename"]
    return p if p.exists() else None


# ── Tulis ─────────────────────────────────────────────────────────────────────

def add_letterhead(
    file_bytes: bytes,
    original_name: str,
    label: str = "",
    lh_type: str = "letterhead",
) -> dict:
    _ensure_dir()
    if lh_type not in TYPES:
        lh_type = "letterhead"
    ext = Path(original_name).suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise ValueError(f"Format fail tidak disokong: {ext}")

    lh_id = "lh_" + uuid.uuid4().hex[:8]
    filename = lh_id + ext
    (_LH_DIR / filename).write_bytes(file_bytes)

    name = label or Path(original_name).stem

    with get_conn() as conn, dict_cur(conn) as cur:
        # Auto-aktifkan jika tiada rekod aktif untuk jenis ini
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM letterheads WHERE type = %s AND is_active = TRUE",
            (lh_type,)
        )
        is_first = cur.fetchone()["cnt"] == 0

        cur.execute("""
            INSERT INTO letterheads (id, name, filename, original_name, type, is_active, uploaded_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (lh_id, name, filename, original_name, lh_type, is_first))

        cur.execute(
            "SELECT id, name, filename, original_name, type, is_active, "
            "uploaded_at AS uploaded FROM letterheads WHERE id = %s",
            (lh_id,)
        )
        return _serial(dict(cur.fetchone()))


def set_active(lh_id: str, lh_type: str = "letterhead") -> bool:
    with get_conn() as conn, dict_cur(conn) as cur:
        # Semak rekod wujud
        cur.execute(
            "SELECT 1 FROM letterheads WHERE id = %s AND type = %s",
            (lh_id, lh_type)
        )
        if not cur.fetchone():
            return False
        # Nyahaktifkan semua → aktifkan yang dipilih
        cur.execute(
            "UPDATE letterheads SET is_active = FALSE WHERE type = %s", (lh_type,)
        )
        cur.execute(
            "UPDATE letterheads SET is_active = TRUE WHERE id = %s", (lh_id,)
        )
    return True


def delete_letterhead(lh_id: str) -> bool:
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute(
            "SELECT filename, type, is_active FROM letterheads WHERE id = %s",
            (lh_id,)
        )
        row = cur.fetchone()
        if not row:
            return False

        # Padam fail fizikal
        p = _LH_DIR / row["filename"]
        if p.exists():
            p.unlink()

        cur.execute("DELETE FROM letterheads WHERE id = %s", (lh_id,))

        # Auto-aktifkan rekod seterusnya jika yang dipadam adalah aktif
        if row["is_active"]:
            cur.execute(
                "SELECT id FROM letterheads WHERE type = %s ORDER BY uploaded_at DESC LIMIT 1",
                (row["type"],)
            )
            next_row = cur.fetchone()
            if next_row:
                cur.execute(
                    "UPDATE letterheads SET is_active = TRUE WHERE id = %s",
                    (next_row["id"],)
                )
    return True


def update_name(lh_id: str, name: str) -> bool:
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute(
            "UPDATE letterheads SET name = %s WHERE id = %s RETURNING id",
            (name, lh_id)
        )
        return cur.fetchone() is not None
