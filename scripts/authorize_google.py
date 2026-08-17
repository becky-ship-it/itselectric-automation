"""
One-time local helper: mint a Google OAuth refresh token for server deploys.

Run this once on your own machine, sign in through the browser, and it prints
the three environment variables to set on Render (or any headless host):

    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GOOGLE_REFRESH_TOKEN

Usage:
    uv run python scripts/authorize_google.py path/to/client_secret.json

The client_secret.json is the OAuth client you downloaded from Google Cloud
(APIs & Services -> Credentials). It must be a "Desktop app" client, or a
"Web application" client with http://localhost added as an authorized redirect
URI, so the local consent flow can complete.
"""

import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore

from itselectric.auth import SCOPES


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/authorize_google.py <client_secret.json>")

    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    # access_type=offline + prompt=consent guarantees a refresh_token is issued.
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    if not creds.refresh_token:
        sys.exit("No refresh token returned. Revoke prior access and retry with prompt=consent.")

    with open(sys.argv[1]) as f:
        client = json.load(f)
    installed = client.get("installed") or client.get("web") or {}

    print("\n# Set these on Render (Environment tab), then deploy:\n")
    print(f"GOOGLE_CLIENT_ID={installed.get('client_id', '')}")
    print(f"GOOGLE_CLIENT_SECRET={installed.get('client_secret', '')}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()
