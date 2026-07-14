"""Google OAuth 2.0 authentication for SMARTAssist Hub."""

import os
from fastapi import APIRouter
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.requests import Request
from authlib.integrations.starlette_client import OAuth
from backend.profile_store import get_profile, save_profile

router = APIRouter()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# Optional: restrict to specific email domains (set to empty list to allow all)
ALLOWED_DOMAINS = os.getenv("ALLOWED_EMAIL_DOMAINS", "").split(",")
ALLOWED_DOMAINS = [d.strip() for d in ALLOWED_DOMAINS if d.strip()]


@router.get("/auth/google")
async def login_via_google(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, str(redirect_uri))


@router.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse("/login?error=auth_failed")

    user = token.get("userinfo")
    if not user:
        return RedirectResponse("/login?error=no_userinfo")

    email = user.get("email", "")

    # Domain restriction check
    if ALLOWED_DOMAINS:
        domain = email.split("@")[-1] if "@" in email else ""
        if domain not in ALLOWED_DOMAINS:
            return RedirectResponse(f"/login?error=unauthorized_domain&email={email}")

    google_sub = user.get("sub", "")
    google_name = user.get("name", "")

    # @moe-dl.edu.my accounts use format "ORGANISASI-NAMA-AKAUN" — extract middle part only
    domain = email.split("@")[-1] if "@" in email else ""
    if domain == "moe-dl.edu.my":
        parts = [p.strip() for p in google_name.split("-")]
        display_name = "-".join(parts[1:-1]).title() if len(parts) >= 3 else google_name.title()
    else:
        display_name = google_name

    request.session["user"] = {
        "email": email,
        "name": display_name,
        "picture": user.get("picture", ""),
        "sub": google_sub,
    }

    # Auto-fill nama from Google — always sync on login so name stays current
    existing = get_profile(google_sub)
    if not existing.get("nama") or existing.get("nama") == google_name:
        save_profile(google_sub, email, {"nama": display_name})

    return RedirectResponse("/")


@router.get("/auth/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse("/login")


def get_current_user(request: Request) -> dict | None:
    return request.session.get("user")
