# itselectric-automation

Automation that uses the Google APIs to process Gmail messages and record extracted data in a Google Sheet.

## What it does

- **Gmail:** Fetches messages by label (e.g. INBOX), decodes body (HTML or plain), and prints a plain-text preview.
- **Extract:** Applies a regex to each body to pull out structured fields for “it’s electric” form emails: **name**, **address**, **email 1**, **email 2**. Non-matching messages are still recorded with empty parsed columns.
- **Sheets:** Optionally appends rows to a Google Sheet with columns: **Sent Date**, **Name**, **Address**, **Email 1**, **Email 2**, **Content**. The script reads existing sheet data, hashes rows, and only appends rows that are not already present (no duplicates on re-run).

## Setup

1. **Environment:** From the repo root run `./run.sh` to create a `venv` and install dependencies. Override with `VENV_DIR=myenv` or `PYTHON=python3.11` if needed.
2. **OAuth:** In [Google Cloud Console](https://console.cloud.google.com/) enable the Gmail API and Google Sheets API, create an OAuth 2.0 Client ID (Desktop app), and save the JSON as `credentials.json` in the repo root. Do not commit this file.
3. **First run:** Run `./run.sh` again; a browser will open for sign-in and the script will create `token.json`. Do not commit `token.json`.

If `credentials.json` is already present, `./run.sh` runs the Python script automatically. Optional arguments: **spreadsheet ID** (to append to a sheet) and **Gmail label** (e.g. INBOX, "Follow Up"):

```bash
./run.sh [SPREADSHEET_ID] [LABEL]
```

With no arguments, the script runs in preview-only mode (default label INBOX). For full control and extra options, activate the venv and run the script directly (see below).

## Usage

**One-shot (recommended when credentials exist):**

```bash
./run.sh                                    # preview only (INBOX)
./run.sh YOUR_SPREADSHEET_ID                # append to sheet, INBOX
./run.sh YOUR_SPREADSHEET_ID "Follow Up"    # append to sheet, label "Follow Up"
./run.sh "" "Follow Up"                     # preview only, label "Follow Up"
```

**Manual run with all options:**

```bash
source venv/bin/activate
python test_script.py [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--label` | INBOX | Gmail label to read (e.g. INBOX, Follow Up). |
| `--max-messages` | 10 | Max number of messages to fetch. |
| `--body-length` | 200 | Max characters of body to print per message (0 = no limit). |
| `--spreadsheet-id` | — | If set, append extracted rows to this Google Sheet (ID from the sheet URL). |
| `--sheet` | Sheet1 | Name of the sheet (tab) inside the spreadsheet. |
| `--content-limit` | 5000 | Max characters for the Content column in Sheets (cell limit 50k). |

**Examples**

```bash
# List and preview up to 5 messages from INBOX (no Sheets)
python test_script.py --label INBOX --max-messages 5

# Same, and append new rows to a Google Sheet (skips rows already on the sheet)
python test_script.py --label INBOX --max-messages 20 --spreadsheet-id "YOUR_SPREADSHEET_ID"

# Use a different tab and cap content length
python test_script.py --spreadsheet-id "YOUR_SPREADSHEET_ID" --sheet "Emails" --content-limit 10000
```

The spreadsheet ID is the long string in the URL:  
`https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`

## Repo layout

- `test_script.py` — Main script: Gmail fetch, regex extraction, optional Sheets append with deduplication.
- `run.sh` — Creates venv, installs from `requirements.txt`, and runs the script (pass spreadsheet ID to append to a sheet).
- `credentials.json` — OAuth client config (you add this; do not commit).
- `token.json` — User tokens (created on first run; do not commit).

## Future work

- Support more extraction patterns or configurable regex.
- Optional filters (e.g. by sender or date range) before extraction/Sheets write.
