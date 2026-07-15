"""User profile storage — saves per-user profile data in PostgreSQL."""

from datetime import datetime
from backend.db import dict_cur, get_conn


def _serial(row: dict) -> dict:
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()}


def get_profile(google_sub: str) -> dict:
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute(
            "SELECT google_sub, email, nama, jawatan, stesen, daerah, negeri, "
            "updated_at AS updated FROM user_profiles WHERE google_sub = %s",
            (google_sub,)
        )
        row = cur.fetchone()
        return _serial(dict(row)) if row else {}


def save_profile(google_sub: str, email: str, data: dict) -> dict:
    allowed = {"nama", "jawatan", "stesen", "daerah", "negeri"}
    fields = {k: v for k, v in data.items() if k in allowed}
    with get_conn() as conn, dict_cur(conn) as cur:
        cur.execute("""
            INSERT INTO user_profiles
                (google_sub, email, nama, jawatan, stesen, daerah, negeri, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (google_sub) DO UPDATE SET
                email   = EXCLUDED.email,
                nama    = CASE WHEN %s != '' THEN %s ELSE user_profiles.nama    END,
                jawatan = CASE WHEN %s != '' THEN %s ELSE user_profiles.jawatan END,
                stesen  = CASE WHEN %s != '' THEN %s ELSE user_profiles.stesen  END,
                daerah  = CASE WHEN %s != '' THEN %s ELSE user_profiles.daerah  END,
                negeri  = CASE WHEN %s != '' THEN %s ELSE user_profiles.negeri  END,
                updated_at = NOW()
        """, (
            google_sub, email,
            fields.get("nama", ""),
            fields.get("jawatan", ""),
            fields.get("stesen", ""),
            fields.get("daerah", ""),
            fields.get("negeri", ""),
            # CASE WHEN pairs
            fields.get("nama", ""),    fields.get("nama", ""),
            fields.get("jawatan", ""), fields.get("jawatan", ""),
            fields.get("stesen", ""),  fields.get("stesen", ""),
            fields.get("daerah", ""),  fields.get("daerah", ""),
            fields.get("negeri", ""),  fields.get("negeri", ""),
        ))
        cur.execute(
            "SELECT google_sub, email, nama, jawatan, stesen, daerah, negeri, "
            "updated_at AS updated FROM user_profiles WHERE google_sub = %s",
            (google_sub,)
        )
        row = cur.fetchone()
        return _serial(dict(row)) if row else {}
