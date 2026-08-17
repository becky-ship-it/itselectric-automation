"""
Google SSO for the web UI, restricted to an email allowlist.

Enforcement is opt-in: it is active only when both ``GOOGLE_OAUTH_CLIENT_ID``
and ``ALLOWED_GOOGLE_EMAILS`` are set. When either is unset (local dev, tests)
the app is open and ``require_user`` is a no-op, so nothing else has to change.

This is deliberately separate from ``src/itselectric/auth.py``, which holds the
inbox owner's *offline* Gmail credentials. Login here only proves *who is using
the dashboard*; it never touches Gmail.
"""

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow  # type: ignore

# Identity-only scopes. Distinct from the Gmail scopes in itselectric.auth.
_SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email"]

router = APIRouter()


def _client_id() -> str | None:
    return os.getenv("GOOGLE_OAUTH_CLIENT_ID")


def _allowlist() -> set[str]:
    raw = os.getenv("ALLOWED_GOOGLE_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def auth_enabled() -> bool:
    """True when SSO is configured. When False the app is open (dev/tests)."""
    return bool(_client_id() and _allowlist())


def check_config() -> None:
    """
    Fail closed on partial config. A single set var (e.g. a typo'd
    ALLOWED_GOOGLE_EMAILS) must not silently leave the app open — refuse to
    boot instead. Both-set (enabled) and both-unset (open dev) are fine.
    """
    id_set = bool(_client_id())
    allow_set = bool(_allowlist())
    if id_set != allow_set:
        missing = "ALLOWED_GOOGLE_EMAILS" if id_set else "GOOGLE_OAUTH_CLIENT_ID"
        raise RuntimeError(
            f"Partial SSO config: {missing} is unset. Set both to enable auth, "
            "or neither to run open. Refusing to start fail-open."
        )


def _flow(redirect_uri: str) -> Flow:
    client_config = {
        "web": {
            "client_id": _client_id(),
            "client_secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(client_config, scopes=_SCOPES, redirect_uri=redirect_uri)


def require_user(request: Request) -> str | None:
    """
    FastAPI dependency: allow the request when auth is disabled or the session
    holds an allowlisted email. Otherwise 401.
    """
    if not auth_enabled():
        return None
    email = request.session.get("user")
    if email and email.lower() in _allowlist():
        return email
    raise HTTPException(status_code=401, detail="authentication required")


def _redirect_uri(request: Request) -> str:
    # Honour the external scheme/host behind Render's proxy.
    base = str(request.base_url).rstrip("/")
    return f"{base}/auth/callback"


@router.get("/auth/login", include_in_schema=False)
def login(request: Request):
    if not auth_enabled():
        return RedirectResponse("/")
    flow = _flow(_redirect_uri(request))
    url, state = flow.authorization_url(prompt="select_account")
    request.session["oauth_state"] = state
    return RedirectResponse(url)


@router.get("/auth/callback", include_in_schema=False)
def callback(request: Request):
    if not auth_enabled():
        return RedirectResponse("/")

    expected = request.session.get("oauth_state")
    if not expected or request.query_params.get("state") != expected:
        raise HTTPException(status_code=400, detail="invalid oauth state")

    flow = _flow(_redirect_uri(request))
    flow.fetch_token(authorization_response=str(request.url))

    info = id_token.verify_oauth2_token(
        flow.credentials.id_token, google_requests.Request(), _client_id()
    )
    email = (info.get("email") or "").lower()
    if not info.get("email_verified") or email not in _allowlist():
        raise HTTPException(status_code=403, detail="account not allowed")

    request.session.pop("oauth_state", None)
    request.session["user"] = email
    return RedirectResponse("/")


@router.post("/auth/logout", include_in_schema=False)
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@router.get("/api/me", tags=["auth"])
def me(request: Request):
    """Return the signed-in email, or null when auth is disabled/anonymous."""
    return {"email": request.session.get("user"), "auth_enabled": auth_enabled()}
