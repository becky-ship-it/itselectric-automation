"""Tests for Google SSO enforcement on the web API."""

import importlib
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_disabled(tmp_path, monkeypatch):
    """Auth env unset → app open, existing behavior preserved."""
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("ALLOWED_GOOGLE_EMAILS", raising=False)
    import server.main

    importlib.reload(server.main)
    monkeypatch.setattr(server.main, "DB_URL", f"sqlite:///{tmp_path}/t.db")
    with TestClient(server.main.app) as c:
        yield c


@pytest.fixture()
def app_enabled(tmp_path, monkeypatch):
    """Auth env set → /api guarded, /auth + /api/me open."""
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-123")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ALLOWED_GOOGLE_EMAILS", "owner@example.com, second@example.com")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    import server.main

    importlib.reload(server.main)
    monkeypatch.setattr(server.main, "DB_URL", f"sqlite:///{tmp_path}/t.db")
    # Secure session cookies (auth enabled) are only sent over https.
    with TestClient(server.main.app, base_url="https://testserver") as c:
        yield c


def test_disabled_allows_api(app_disabled):
    assert app_disabled.get("/api/config").status_code == 200


def test_disabled_me_reports_off(app_disabled):
    body = app_disabled.get("/api/me").json()
    assert body == {"email": None, "auth_enabled": False}


def test_enabled_blocks_api_without_session(app_enabled):
    assert app_enabled.get("/api/config").status_code == 401


def test_enabled_me_is_open(app_enabled):
    body = app_enabled.get("/api/me").json()
    assert body["auth_enabled"] is True
    assert body["email"] is None


def test_enabled_login_redirects_to_google(app_enabled):
    resp = app_enabled.get("/auth/login", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "accounts.google.com" in resp.headers["location"]


def test_allowlist_parsing(app_enabled):
    """Comma-separated ALLOWED_GOOGLE_EMAILS is parsed, trimmed, lowercased."""
    from server.auth import _allowlist

    allow = _allowlist()
    assert allow == {"owner@example.com", "second@example.com"}
    assert "intruder@example.com" not in allow


def test_callback_rejects_state_mismatch(app_enabled):
    """A session with a known state + a different callback state → 400."""
    app_enabled.get("/auth/login", follow_redirects=False)  # seeds session oauth_state
    resp = app_enabled.get("/auth/callback?state=wrong&code=x", follow_redirects=False)
    assert resp.status_code == 400


def test_spa_fallback_guard_confines_to_dist(tmp_path):
    """The resolved-path guard: an outside file resolves outside _DIST and so
    fails is_relative_to, while a real in-dir file passes. This is the exact
    predicate spa_fallback uses before serving."""
    dist = (tmp_path / "web" / "dist").resolve()
    dist.mkdir(parents=True)
    (dist / "app.js").write_text("ok")
    (tmp_path / "secret.txt").write_text("root:x:0:0")

    escaped = (dist / "../../secret.txt").resolve()
    inside = (dist / "app.js").resolve()
    assert not (escaped.is_file() and escaped.is_relative_to(dist))
    assert inside.is_file() and inside.is_relative_to(dist)


def _run_callback(client, info):
    """Drive login→callback with a mocked Google exchange returning `info`."""
    from unittest.mock import MagicMock

    flow = MagicMock()
    flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth", "S1")
    flow.credentials.id_token = "tok"
    with (
        patch("server.auth._flow", return_value=flow),
        patch("server.auth.id_token.verify_oauth2_token", return_value=info),
    ):
        client.get("/auth/login", follow_redirects=False)  # seeds oauth_state=S1
        return client.get("/auth/callback?state=S1&code=x", follow_redirects=False)


def test_callback_allows_allowlisted_verified_email(app_enabled):
    resp = _run_callback(app_enabled, {"email": "owner@example.com", "email_verified": True})
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/"
    assert app_enabled.get("/api/config").status_code == 200  # session now valid


def test_callback_rejects_non_allowlisted_email(app_enabled):
    resp = _run_callback(app_enabled, {"email": "intruder@example.com", "email_verified": True})
    assert resp.status_code == 403


def test_callback_rejects_unverified_email(app_enabled):
    resp = _run_callback(app_enabled, {"email": "owner@example.com", "email_verified": False})
    assert resp.status_code == 403


def test_partial_config_refuses_to_boot(tmp_path, monkeypatch):
    """Only one of the two SSO vars set → check_config raises (no silent open)."""
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-123")
    monkeypatch.delenv("ALLOWED_GOOGLE_EMAILS", raising=False)
    import server.auth

    importlib.reload(server.auth)
    with pytest.raises(RuntimeError, match="Partial SSO config"):
        server.auth.check_config()
