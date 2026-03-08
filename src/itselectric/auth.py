"""Google OAuth credential management."""

import os
import os.path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def get_credentials(
    token_file: str = TOKEN_FILE,
    credentials_file: str = CREDENTIALS_FILE,
) -> Credentials:
    """Return valid Google OAuth credentials, refreshing or re-authenticating as needed."""
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
