"""
backend/login_logger.py
=======================
Catat setiap percubaan log masuk ke jadual login_history dan audit_logs.
"""
from __future__ import annotations
from backend.db import get_conn, dict_cur


def log_login(
    *,
    google_sub: str | None,
    email: str | None,
    success: bool,
    failure_reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Tulis satu rekod ke login_history dan (jika berjaya) ke audit_logs."""
    try:
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                """
                INSERT INTO login_history
                    (google_sub, email, success, failure_reason, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (google_sub, email, success, failure_reason, ip_address, user_agent),
            )

            if success and google_sub:
                cur.execute(
                    """
                    INSERT INTO audit_logs
                        (google_sub, email, action, resource_type, detail, ip_address, user_agent)
                    VALUES (%s, %s, 'login', 'session', '{}'::jsonb, %s, %s)
                    """,
                    (google_sub, email, ip_address, user_agent),
                )
    except Exception:
        pass  # jangan biarkan logging error kacau aliran login


def log_audit(
    *,
    request,
    action: str,
    resource_type: str,
    detail: dict | None = None,
) -> None:
    """Catat tindakan pengguna ke audit_logs. Selamat dipanggil dari mana-mana endpoint."""
    from auth import get_current_user
    user = get_current_user(request)
    if not user:
        return
    try:
        import json as _json
        with get_conn() as conn, dict_cur(conn) as cur:
            cur.execute(
                """
                INSERT INTO audit_logs
                    (google_sub, email, action, resource_type, detail, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user.get("sub"),
                    user.get("email"),
                    action,
                    resource_type,
                    _json.dumps(detail or {}),
                    _get_client_ip(request),
                    _get_user_agent(request),
                ),
            )
    except Exception:
        pass


def _get_client_ip(request) -> str | None:
    """Ambil IP sebenar klien — ambil kira reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _get_user_agent(request) -> str | None:
    return request.headers.get("user-agent")
