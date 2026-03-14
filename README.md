# itselectric-automation

Automation that reads Gmail messages matching a label, extracts structured fields from
"It's Electric" contact-form emails, geocodes the extracted address, finds the nearest
EV charger, and appends new rows to a Google Sheet.

---

## What it does

1. **Fetch** — Reads Gmail messages by label (e.g. `INBOX`, `Follow Up`) via the Gmail API, or loads `.txt` files from a local directory (no auth required — useful for testing and local dev).
2. **Extract** — Applies a regex to each plain-text body to pull out structured fields: **name**, **address**, **email 1**, **email 2**. Messages that don't match are still recorded with empty parsed columns.
3. **Geocode** — Converts the extracted address to latitude/longitude using the Nominatim geocoder (OpenStreetMap). Results are cached in a local JSON file so each address is only looked up once.
4. **Proximity** — Finds the nearest EV charger from a bundled CSV of charger locations, computing straight-line distance in miles.
5. **Write** — Appends rows to a Google Sheet with columns: **Sent Date**, **Name**, **Address**, **Email 1**, **Email 2**, **Content**, **Nearest Charger**, **Distance (mi)**. Rows are hashed before writing — re-running never creates duplicates.

---

## Repository layout

```
src/itselectric/
  auth.py        — OAuth credential loading/refresh (token.json + credentials.json)
  cli.py         — argparse entry point; orchestrates all modules
  extract.py     — Regex extraction: name, address, email_1, email_2
  fixture.py     — File-based email source (reads .txt files instead of Gmail)
  geo.py         — Address geocoding (Nominatim + disk cache) and charger proximity
  gmail.py       — Gmail API: fetch messages, decode multipart bodies, strip HTML
  gui.py         — CustomTkinter dark-mode GUI; calls modules directly (not subprocess)
  sheets.py      — Sheets API: hash-based deduplication, append rows
  data/
    chargers.csv — Bundled EV charger locations (STREET, CITY, STATE, LAT, LONG, …)

tests/
  fixtures/
    emails/      — Sample .txt email bodies for integration testing
  test_extract.py       — Unit tests for extraction regex
  test_fixture.py       — Unit tests for file-based email source
  test_geo.py           — Unit tests for geocoding, caching, and proximity
  test_gmail.py         — Unit tests for Gmail body decoding and date formatting
  test_gui_pipeline.py  — Unit tests for GUI pipeline orchestration
  test_integration.py   — End-to-end integration tests (no network, no credentials)
  test_sheets.py        — Unit tests for hashing/dedup logic

docs/plans/      — Implementation plan documents
app.spec         — PyInstaller spec → builds "it's electric automation.app"
build_app.sh     — Run ./build_app.sh to produce dist/it's electric automation.app
config.example.yaml — Template for config.yaml (commit this, not config.yaml)
pyproject.toml   — Package config, dependencies, entry points, linting/test settings
run.sh           — Legacy shell runner (venv-based, no uv required)

# Gitignored (you create these):
credentials.json — OAuth client config (never commit)
token.json       — User tokens created on first auth run (never commit)
config.yaml      — Your local config (never commit)
geocache.json    — Address geocoding cache (auto-created, safe to commit or gitignore)
```

---

## Setup

### 1. Install dependencies

```bash
uv sync          # installs runtime deps
uv sync --extra dev  # also installs pytest, ruff, pyinstaller
```

### 2. Google API credentials (skip if using fixture mode)

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Gmail API** and **Google Sheets API** for your project.
3. Create an **OAuth 2.0 Client ID** (Desktop app type).
4. Download the JSON and save it as `credentials.json` in the repo root.
5. **Never commit `credentials.json`** — it is gitignored.

On first run a browser window opens for sign-in. The script saves `token.json`
automatically. If the token expires or is revoked, it deletes itself and re-authenticates
on the next run.

### 3. Config file

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your spreadsheet ID, label, and other settings. This file is
gitignored — never commit it.

---

## Configuration

All settings live in `config.yaml` (copied from `config.example.yaml`). CLI flags override
config values when both are present.

| Key | Default | CLI flag | Description |
|-----|---------|----------|-------------|
| `label` | `INBOX` | `--label` | Gmail label to read (`INBOX`, `Follow Up`, etc.) |
| `max_messages` | `100` | `--max-messages` | Maximum number of messages to fetch |
| `body_length` | `200` | `--body-length` | Max characters of body to print per message (0 = no limit) |
| `spreadsheet_id` | `""` | `--spreadsheet-id` | Google Spreadsheet ID from the sheet URL. If empty, runs in preview-only mode (no Sheet write) |
| `sheet` | `Sheet1` | `--sheet` | Sheet (tab) name within the spreadsheet |
| `content_limit` | `5000` | `--content-limit` | Max characters for the Content column |
| `chargers` | *(bundled CSV)* | `--chargers` | Path to chargers CSV. Defaults to the bundled `src/itselectric/data/chargers.csv` |
| `geocache` | `geocache.json` | `--geocache` | Path to JSON file used to cache geocoded addresses. Created automatically on first run |
| `fixture_dir` | `""` | `--fixture-dir` | Load emails from `.txt` files in this directory instead of Gmail. **Skips all Google auth.** |

The spreadsheet ID is the long string in the sheet URL:
```
https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
```

### Chargers CSV format

The bundled `src/itselectric/data/chargers.csv` has these columns:

| Column | Description |
|--------|-------------|
| `STREET` | Street address |
| `CITY` | City |
| `STATE` | State abbreviation |
| `ZIPCODE` | ZIP code |
| `CHARGERID` | Charger ID(s) at this location |
| `NUM_OF_CHARGERS` | Number of chargers |
| `LAT` | Latitude |
| `LONG` | Longitude |
| `LAT_OVERRIDE` | Corrected latitude (used instead of LAT when non-empty) |
| `LONG_OVERRIDE` | Corrected longitude (used instead of LONG when non-empty) |

To use a custom charger list, provide a CSV with the same columns and set `chargers` in
`config.yaml`.

---

## Running

### CLI

```bash
# Uses config.yaml
uv run itselectric

# Override specific settings
uv run itselectric --label "Follow Up"
uv run itselectric --spreadsheet-id "YOUR_SPREADSHEET_ID"
uv run itselectric --max-messages 10 --body-length 0

# Run without Gmail (no credentials needed)
uv run itselectric --fixture-dir tests/fixtures/emails
```

### GUI (development)

```bash
uv run itselectric-gui
```

### GUI (macOS app)

```bash
./build_app.sh
# → dist/it's electric automation.app
```

Drag the `.app` to `/Applications`. First launch: right-click → **Open** → **Open Anyway**
(macOS Gatekeeper, one-time only).

Put `config.yaml` and `credentials.json` in the same folder as the app, then browse for
`config.yaml` in the GUI and click **Run**. Pipeline output streams into the log in real time.

To use fixture mode in the GUI, add `fixture_dir: tests/fixtures/emails` to your
`config.yaml` — the GUI reads and respects this key.

### Legacy shell runner (no `uv` required)

```bash
./run.sh                                      # preview only, INBOX
./run.sh YOUR_SPREADSHEET_ID                  # append to sheet, INBOX
./run.sh YOUR_SPREADSHEET_ID "Follow Up"      # append to sheet, custom label
./run.sh "" "Follow Up"                       # preview only, custom label
```

---

## Geocoding and caching

Addresses are geocoded using [Nominatim](https://nominatim.openstreetmap.org/) (OpenStreetMap),
which is free but rate-limited to **1 request per second** per their Terms of Service.
The `geopy` `RateLimiter` wrapper enforces this automatically.

Results are written to `geocache.json` (configurable via `geocache` config key) so each
unique address is only ever geocoded once. The cache is a plain JSON file:

```json
{
  "123 Main St, Brooklyn, NY 11205": [40.6892, -73.9442],
  "456 Elm Ave, Boston, MA 02115": [42.3451, -71.0893]
}
```

You can pre-populate `geocache.json` with known addresses to avoid any API calls at all —
this is exactly what the integration tests do.

---

## Testing

### Run all tests

```bash
uv run pytest
# or, if uv has PATH issues:
.venv/bin/python -m pytest -v
```

### Test suite overview

| File | What it covers |
|------|---------------|
| `test_extract.py` | Regex extraction — parsed matches, no-match, empty, None input |
| `test_fixture.py` | `load_fixture_messages` — body roundtrip, date parsing, sort order, non-txt filtering, empty dir, missing dir |
| `test_geo.py` | `load_chargers` (LAT_OVERRIDE fallback), `geocode_address` (cache read/write/hit, not-found, empty), `find_nearest_charger` |
| `test_gmail.py` | `get_body_from_payload` (single-part, multipart, nested), `body_to_plain` (HTML stripping), `format_sent_date` |
| `test_gui_pipeline.py` | `_run_pipeline` completion guarantees, stdout restoration, success/failure message routing |
| `test_integration.py` | Full end-to-end: fixture files → extract → geocache → nearest charger → 8-element row tuples |
| `test_sheets.py` | `row_hash` deduplication — parsed vs unparsed hash strategies |

### Running a specific file or test

```bash
uv run pytest tests/test_geo.py -v
uv run pytest tests/test_integration.py::TestFullPipeline::test_full_row_building -v
```

### Integration tests (no network, no credentials)

The integration tests in `tests/test_integration.py` exercise the full pipeline against
real fixture files without hitting any external API:

```bash
uv run pytest tests/test_integration.py -v
```

They work by:
1. Loading emails from `tests/fixtures/emails/*.txt` via `load_fixture_messages`
2. Using a pre-populated in-memory geocache — no Nominatim calls
3. Loading the real bundled `chargers.csv`
4. Asserting correct extraction, geo lookup, and row structure

**No `credentials.json` or `token.json` is needed to run the integration tests.**

### Developing new tests without Google credentials

Use `--fixture-dir` to iterate on the full pipeline locally:

```bash
# Run CLI end-to-end with fixture emails
uv run itselectric --fixture-dir tests/fixtures/emails

# Add a new fixture file and re-run
echo "it's electric Alice Lee The user has an address of 1 Main St, Portland, ME 04101 and has an email of
alice@example.com
Email address submitted in form
alice2@example.com" > tests/fixtures/emails/04_alice.txt

uv run itselectric --fixture-dir tests/fixtures/emails
```

### Adding fixture emails

Each fixture email is a plain `.txt` file in `tests/fixtures/emails/`. Files are loaded
in sorted filename order. The format must match the extraction regex in `extract.py`:

```
it's electric <Name> The user has an address of <Address> and has an email of
<email_1>
Email address submitted in form
<email_2>
```

For unparsed emails (to test the fallback path), any text that does not match this
pattern will be recorded as a raw content row with empty parsed columns.

---

## Adding new extraction patterns

The extraction regex lives entirely in `src/itselectric/extract.py`:

```python
EXTRACT_PATTERN = re.compile(
    r"\[plain\]: it's electric (?P<name>.*?) "
    r"The user has an address of (?P<address>.*?) "
    r"and has an email of\s+(?P<email_1>\S+)\s+"
    r"Email address submitted in form\s+(?P<email_2>\S+)"
)
```

Note: `extract_parsed` prepends `"[plain]: "` to the content before matching, so fixture
files and raw email bodies should **not** include that prefix.

To add a new pattern or support a different email format:
1. Edit `EXTRACT_PATTERN` in `src/itselectric/extract.py`.
2. Add a corresponding fixture file in `tests/fixtures/emails/` with sample content.
3. Add unit tests in `tests/test_extract.py`.
4. Run `uv run pytest tests/test_extract.py tests/test_integration.py -v`.

---

## Linting

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

The project uses ruff with rules `E`, `F`, `I` and a line length of 100.

---

## Key design decisions

**Deduplication via hashing.** Before writing, every row is hashed. Parsed rows hash
on `(date, name, address, email_1, email_2)`. Unparsed rows hash on `(date, content)`.
This means the script can be re-run safely at any time without creating duplicates, even
if the sheet already has partial data.

**Geocoding cache.** The Nominatim geocoder enforces 1 req/sec. The JSON cache ensures
each address is only ever geocoded once across all runs. The cache path is configurable
and defaults to `geocache.json` in the working directory (next to `config.yaml` when
running from the GUI).

**File-based email source.** `fixture.py` lets the full pipeline run without any Google
credentials by encoding `.txt` file contents as base64 in Gmail-compatible message dicts.
Every downstream module (`gmail.py`, `extract.py`, `geo.py`, `sheets.py`) works
identically whether messages came from Gmail or files.

**Deferred imports in the GUI.** All `itselectric.*` imports inside `gui.py:_run_pipeline`
are deferred (inside the method body). This allows PyInstaller to correctly tree-shake
the dependency graph when building the `.app` bundle.

**LAT_OVERRIDE / LONG_OVERRIDE.** Some charger rows in the CSV have manually corrected
coordinates in these columns. `load_chargers` uses the override values when both are
non-empty, falling back to the primary `LAT`/`LONG` columns otherwise.
