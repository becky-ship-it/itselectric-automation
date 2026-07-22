# Google OAuth Setup

Google credentials are required to fetch Gmail messages, send follow-up emails, or use the optional Google Sheets export. Fixture runs with auto-send off do not need them.

## Create OAuth credentials

1. In [Google Cloud Console](https://console.cloud.google.com/), create or select a project.
2. Open **APIs & Services** → **Library** and enable:
   - Gmail API
   - Google Sheets API, only if using legacy Sheets export
3. Open **APIs & Services** → **OAuth consent screen**. Complete the required fields. If the app is in testing, add each operator under **Test users**.
4. Open **APIs & Services** → **Credentials** → **Create credentials** → **OAuth client ID**.
5. Choose **Desktop app**, create the client, and download its JSON file.
6. Rename the downloaded file to `credentials.json` and place it in the repository root.

`credentials.json` is an OAuth client secret. It and the generated `token.json` are gitignored; never commit or share them.

## Authorize locally

1. Start the app with `./run_server.sh`.
2. Open `http://localhost:8000` and run the Gmail pipeline, or send an email manually.
3. The app opens a browser window for Google sign-in and consent. Complete the flow with an account that can access the configured Gmail label.
4. The app saves the resulting refresh token as `token.json` in the repository root.

The app requests Gmail read/label and send access. It also requests Google Sheets access for optional legacy export.

## Re-authorize

Delete `token.json` and run a Gmail operation again if the token is revoked, you switch Google accounts, or you replace `credentials.json`. The app will reopen the browser consent flow.

## Troubleshooting

- **`credentials.json` not found:** Download a Desktop OAuth client JSON file and save it in the repository root with that exact name.
- **Access blocked or test-user error:** Add the Google account to the OAuth consent screen's test users, or publish the consent screen according to your organization's policy.
- **Wrong Google account:** Delete `token.json`, then authorize again in a browser session signed in to the intended account.
