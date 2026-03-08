# itselectric-automation

Automation that uses the Google APIs to process Gmail messages and record extracted data in a Google Sheet.

## What it does

- **Gmail:** Fetches messages by label (e.g. INBOX), decodes body (HTML or plain), and prints a plain-text preview.
- **Extract:** Applies a regex to each body to pull out structured fields for "it's electric" form emails: **name**, **address**, **email 1**, **email 2**. Non-matching messages are still recorded with empty parsed columns.
- **Sheets:** Optionally appends rows to a Google Sheet with columns: **Sent Date**, **Name**, **Address**, **Email 1**, **Email 2**, **Content**. Rows are hashed before writing — re-running never creates duplicates.

## Setup

1. **OAuth:** In [Google Cloud Console](https://console.cloud.google.com/) enable the Gmail API and Google Sheets API, create an OAuth 2.0 Client ID (Desktop app), and save the JSON as `credentials.json` in the repo root. Do not commit this file.

2. **Config:** Copy the example config and fill in your values:
   ```bash
   cp config.example.yaml config.yaml
   ```
   Edit `config.yaml` with your spreadsheet ID, label, and any other settings. This file is gitignored — do not commit it.

3. **Install dependencies:**
   ```bash
   # Recommended
   uv sync

   # Or with the legacy shell runner (creates a venv automatically)
   ./run.sh
   ```

4. **First run:** A browser will open for Google sign-in. The script creates `token.json` automatically. Do not commit this file. If the token expires or is revoked, it is deleted and re-created automatically on the next run.

## Configuration

All settings can be defined in `config.yaml` (copy from `config.example.yaml`). CLI flags override config values when provided.

| Key | Default | Description |
|-----|---------|-------------|
| `label` | `INBOX` | Gmail label to read (e.g. `INBOX`, `Follow Up`). |
| `max_messages` | `100` | Max number of messages to fetch. |
| `body_length` | `200` | Max characters of body to print per message (0 = no limit). |
| `spreadsheet_id` | — | Google Spreadsheet ID from the sheet URL. If not set, runs in preview-only mode. |
| `sheet` | `Sheet1` | Name of the sheet (tab) inside the spreadsheet. |
| `content_limit` | `5000` | Max characters for the Content column in Sheets. |

The spreadsheet ID is the long string in the sheet URL:
`https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`

## Usage

**With `uv` (recommended):**

```bash
uv run itselectric                            # uses config.yaml
uv run itselectric --label "Follow Up"        # override label only
uv run itselectric --spreadsheet-id "YOUR_ID" # override spreadsheet only
```

**With the legacy shell runner:**

```bash
./run.sh                                    # uses config.yaml settings
./run.sh YOUR_SPREADSHEET_ID                # append to sheet, INBOX
./run.sh YOUR_SPREADSHEET_ID "Follow Up"    # append to sheet, custom label
./run.sh "" "Follow Up"                     # preview only, custom label
```

Note: CLI flags passed to `run.sh` take precedence over `config.yaml`.

## Desktop App (macOS)

A polished dark-mode GUI is included. Build it as a double-clickable macOS `.app`:

```bash
./build_app.sh
# → dist/it's electric automation.app
```

Drag `dist/it's electric automation.app` to your `/Applications` folder.
First launch: right-click → **Open** → **Open Anyway** (macOS Gatekeeper, one-time only).

Put your `config.yaml` and `credentials.json` in the same folder, then browse for `config.yaml` in the app and click **Run**. Pipeline output streams into the log in real time.

To run the GUI without building the app:
```bash
uv run itselectric-gui
```

## Repo layout

```
src/itselectric/
  auth.py      — OAuth credential management (auto-recovers revoked tokens)
  gmail.py     — Gmail API: fetch, decode multipart bodies, strip HTML
  extract.py   — Regex extraction: name, address, email_1, email_2
  sheets.py    — Sheets API: hash-based deduplication, append rows
  cli.py       — CLI entry point: loads config.yaml, parses args, orchestrates
  gui.py       — CustomTkinter desktop GUI
tests/
  test_extract.py   — Unit tests for extraction regex
  test_sheets.py    — Unit tests for hashing/dedup logic
app.spec            — PyInstaller spec for building the macOS .app
build_app.sh        — One-command build script
config.example.yaml — Template for config.yaml (commit this, not config.yaml)
pyproject.toml      — Package config, dependencies, linting, test settings
run.sh              — Legacy shell runner (venv-based, no uv required)
credentials.json    — OAuth client config (you add this; do not commit)
token.json          — User tokens (created on first run; do not commit)
```

## Development

```bash
# Install with dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Lint
uv run ruff check src/ tests/
```

## Future work

- Support more extraction patterns or configurable regex.
- Optional filters (e.g. by sender or date range) before extraction/Sheets write.
