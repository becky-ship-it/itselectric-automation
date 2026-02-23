# itselectric-automation

Automation that uses the Google APIs to process Gmail messages and record extracted data in a Google Sheet.

## Current status

**Done**

- OAuth for Google API is set up and verified. The test script (`test_script.py`) uses the Gmail API quickstart flow to list Gmail labels and confirms that credentials and token work.

**Setup**

1. Put your OAuth client config from [Google Cloud Console](https://console.cloud.google.com/) (APIs & Services → Credentials → OAuth 2.0 Client ID, type “Desktop app”) in `credentials.json`. Do not commit this file.
2. Run the test script once; a browser will open for sign-in and the script will create `token.json` with user tokens. Do not commit `token.json`.
3. Run: `python3 test_script.py` (with venv activated if you use one).

## Future work

- **Read emails** – Use the Gmail API to fetch messages (e.g. by label or query).
- **Classify** – Classify messages (e.g. by sender, subject, or content).
- **Extract info** – Parse and extract structured data from each message (e.g. amounts, dates, reference numbers).
- **Write to Google Sheet** – Use the Google Sheets API to append or update rows with the extracted information.

All of this will use the same OAuth setup (Gmail + Sheets scopes as needed).
