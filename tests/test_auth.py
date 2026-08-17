"""Tests for Google OAuth credential resolution."""

from unittest.mock import MagicMock, patch

from itselectric.auth import _credentials_from_env, get_credentials


class TestCredentialsFromEnv:
    def test_returns_none_when_env_incomplete(self, monkeypatch):
        """Missing any of the three env vars → None (fall back to file flow)."""
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "s")
        monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "r")
        assert _credentials_from_env() is None

    def test_builds_and_refreshes_from_env(self, monkeypatch):
        """All three env vars present → build creds and refresh (mint access token)."""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "refresh")

        with patch("itselectric.auth.Credentials") as mock_creds:
            instance = MagicMock()
            mock_creds.return_value = instance
            result = _credentials_from_env()

        assert result is instance
        instance.refresh.assert_called_once()
        kwargs = mock_creds.call_args.kwargs
        assert kwargs["refresh_token"] == "refresh"
        assert kwargs["client_id"] == "id"
        assert kwargs["client_secret"] == "secret"


class TestGetCredentials:
    def test_prefers_env_over_files(self, monkeypatch):
        """When env creds resolve, no file/browser flow is attempted."""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
        monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "refresh")

        sentinel = MagicMock()
        with (
            patch("itselectric.auth._credentials_from_env", return_value=sentinel),
            patch("itselectric.auth.InstalledAppFlow") as mock_flow,
            patch("itselectric.auth.os.path.exists", return_value=False) as mock_exists,
        ):
            result = get_credentials()

        assert result is sentinel
        mock_flow.from_client_secrets_file.assert_not_called()
        mock_exists.assert_not_called()
