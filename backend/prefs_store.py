"""
backend/prefs_store.py
======================
Baca dan simpan keutamaan pengguna dari jadual user_preferences.
"""
from __future__ import annotations
from backend.db import get_conn, dict_cur

_DEFAULTS = {
    "language": "bm",
    "default_agent": "letter_generator",
    "email_notifications": False,
    "theme": "dark",
}


def get_prefs(google_sub: str) -> dict:
    """Kembalikan keutamaan pengguna. Jika belum ada rekod, kembalikan nilai lalai."""
    try:
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                "SELECT language, default_agent, email_notifications, theme "
                "FROM user_preferences WHERE google_sub = %s",
                (google_sub,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "language": row["language"],
                    "default_agent": row["default_agent"],
                    "email_notifications": row["email_notifications"],
                    "theme": row["theme"],
                }
    except Exception:
        pass
    return dict(_DEFAULTS)


def save_prefs(google_sub: str, data: dict) -> dict:
    """Kemaskini keutamaan pengguna. Hanya medan yang dihantar sahaja dikemaskini."""
    allowed = {"language", "default_agent", "email_notifications", "theme"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return get_prefs(google_sub)

    try:
        with get_conn() as conn, dict_cur(conn) as cur:
            # Upsert — cipta baris baru jika belum ada
            cur.execute(
                """
                INSERT INTO user_preferences (google_sub, language, default_agent, email_notifications, theme)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (google_sub) DO UPDATE SET
                    language            = EXCLUDED.language,
                    default_agent       = EXCLUDED.default_agent,
                    email_notifications = EXCLUDED.email_notifications,
                    theme               = EXCLUDED.theme,
                    updated_at          = NOW()
                """,
                (
                    google_sub,
                    updates.get("language", _DEFAULTS["language"]),
                    updates.get("default_agent", _DEFAULTS["default_agent"]),
                    updates.get("email_notifications", _DEFAULTS["email_notifications"]),
                    updates.get("theme", _DEFAULTS["theme"]),
                ),
            )
    except Exception:
        pass

    return get_prefs(google_sub)
