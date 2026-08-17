"""Google OAuth credential management."""

import os
import os.path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def _credentials_from_env() -> Credentials | None:
    """
    Build credentials from environment variables, for headless/server deploys.

    Requires GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN.
    Returns None when any are unset, so callers can fall back to the local
    file-based flow. The access token is minted on first refresh.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh_token):
        return None

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def get_credentials(
    token_file: str = TOKEN_FILE,
    credentials_file: str = CREDENTIALS_FILE,
) -> Credentials:
    """
    Return valid Google OAuth credentials.

    On a server, set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET /
    GOOGLE_REFRESH_TOKEN and credentials are built from those with no browser
    or local files. When those are unset (local dev), fall back to the
    file-based flow: reuse token.json, refresh it, or run a one-time browser
    consent from credentials.json.
    """
    env_creds = _credentials_from_env()
    if env_creds is not None:
        return env_creds

    creds = None
    if os.path.exists(token_file):
        print("Token file exists")
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    else:
        print("No token file found")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                print("Token expired or revoked. Deleting token and re-authenticating...")
                os.remove(token_file)
                creds = None
        if not creds or not creds.valid:
            print("No valid credentials available, creating new ones")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            print(f"Saving credentials to {token_file}")
            f.write(creds.to_json())

    return creds
