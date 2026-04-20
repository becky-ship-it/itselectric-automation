# Repo Overview: itselectric-automation

Python pipeline that reads "It's Electric" EV contact-form emails from Gmail, extracts structured fields via regex, geocodes the address, finds the nearest charger, routes to an email template via a decision tree, sends the email via Gmail, and optionally writes rows to Google Sheets and upserts contacts into HubSpot CRM.

---

## Repository Layout

```
/
├── src/itselectric/
│   ├── __init__.py
│   ├── auth.py             # Google OAuth credential management
│   ├── cli.py              # CLI entry point — argparse + main pipeline loop
│   ├── gui.py              # macOS desktop GUI (CustomTkinter) — being replaced by web app
│   ├── extract.py          # regex extraction from email bodies
│   ├── fixture.py          # local .txt email source for dev/testing
│   ├── geo.py              # geocoding (Nominatim) + charger proximity
│   ├── gmail.py            # Gmail API: fetch, decode, send, load templates
│   ├── docs.py             # Google Docs template fetching (Drive API)
│   ├── sheets.py           # Google Sheets API: dedup + append
│   ├── hubspot.py          # HubSpot CRM: upsert contacts
│   ├── decision_tree.py    # YAML decision tree evaluator
│   └── data/
│       ├── chargers.csv        # bundled EV charger locations (26 entries)
│       └── request_template.txt
├── tests/
│   ├── fixtures/emails/        # 10 .txt fixture files for offline testing
│   ├── test_decision_tree.py
│   ├── test_decision_tree_pipeline.py
│   ├── test_docs.py
│   ├── test_extract.py
│   ├── test_fixture.py
│   ├── test_geo.py
│   ├── test_gmail.py
│   ├── test_gui_pipeline.py
│   ├── test_hubspot.py
│   ├── test_integration.py
│   └── test_sheets.py
├── docs/
│   ├── repo-overview.md        # this file
│   ├── email-template-guide.md
│   ├── configuration.md
│   ├── hubspot.md
│   ├── testing.md
│   └── plans/
├── config.example.yaml
├── config.yaml             # gitignored, live config
├── decision_tree.example.yaml
├── decision_tree.yaml      # gitignored, live routing tree
├── geocache.json           # gitignored, address → lat/lon cache
├── credentials.json        # gitignored, Google OAuth client secrets
├── token.json              # gitignored, saved OAuth tokens
├── pyproject.toml
├── app.spec                # PyInstaller spec for macOS .app (deprecated)
└── build_app.sh            # macOS app build script (deprecated)
```

---

## End-to-End Data Flow

```
Gmail label (e.g. "Follow Up")
  ↓  fetch_messages() → list of raw Gmail message dicts
  │  OR
  └─ load_fixture_messages() → same dict shape from local .txt files

Per message:
  ↓  get_body_from_payload() → (mime_type, raw_text)
  ↓  body_to_plain()         → stripped plain text (BeautifulSoup strips HTML)
  ↓  extract_parsed()        → {"name", "address", "email_1", "email_2"} or None

If parsed:
  ↓  upsert_contact()        → HubSpot CRM contact ID (if token configured)
  ↓  geocode_address()       → (lat, lon) via Nominatim, cached to geocache.json
  ↓  find_nearest_charger()  → (charger_dict, distance_miles)
  ↓  _build_tree_context()   → {"driver_state", "charger_state", "charger_city", "distance_miles"}
  ↓  evaluate(tree, ctx)     → template_name (str) or None

  ↓  fetch_template_from_doc(creds, google_doc_id, template_name)  ← priority
  │  OR load_template(template_name, template_dir)                 ← fallback
  ↓  body.format_map({"name", "address", "city", "state"})
  ↓  send_email(creds, email_1, subject, body)

Collect 10-column tuple per message:
  (sent_date, name, address, email_1, email_2, content,
   nearest_charger, distance_mi, contact_status, email_status)

If spreadsheet_id configured:
  ↓  get_existing_hashes() → SHA-256 set of existing rows
  ↓  filter duplicates
  ↓  append_rows()         → Google Sheets API append
```

---

## Modules

### `auth.py`

Manages the Google OAuth 2.0 token lifecycle. Single public function.

**`get_credentials(token_file="token.json", credentials_file="credentials.json") → Credentials`**

1. Reads `token.json` if it exists, validates against SCOPES
2. If expired + refresh token: calls `creds.refresh(Request())`
3. If `RefreshError` (revoked): deletes `token.json`, falls through
4. If no valid creds: `InstalledAppFlow.run_local_server(port=0)` (opens browser)
5. Writes updated token back to `token.json`

**Scopes:**

| Scope | Purpose |
|-------|---------|
| `gmail.modify` | Read + label Gmail messages |
| `gmail.send` | Send reply emails |
| `spreadsheets` | Read/write Google Sheets |
| `drive.readonly` | Export Google Docs for email templates |

> **Note:** `drive.readonly` was added for the Google Docs template system. Existing deployments must delete `token.json` and re-auth once.

---

### `extract.py`

Pure regex extraction. No I/O.

**`extract_parsed(content: str) → dict | None`**

Matches the specific text format of "It's Electric" contact form emails:

```
[plain]: it's electric <Name> The user has an address of <Address>
and has an email of
<email_1>
Email address submitted in form
<email_2>
```

Returns `{"name", "address", "email_1", "email_2"}` on match, `None` otherwise.

---

### `fixture.py`

**`load_fixture_messages(directory) → list[dict]`**

Reads all `.txt` files from a directory, base64url-encodes their content into Gmail-shaped payload dicts, uses file `mtime` as `internalDate`. Returns identical structure to the Gmail API — the rest of the pipeline can't tell the difference. Used for offline development.

---

### `gmail.py`

Gmail API wrapper.

**`fetch_messages(creds, label, max_messages) → list[dict]`**
- Resolves label name → ID via `labels().list()`
- Fetches message IDs via `messages().list()`
- Fetches full message per ID via `messages().get()`

**`get_body_from_payload(payload) → (mime_type, text) | (None, None)`**
- Handles single-part, multipart, and nested multipart messages
- Recursively collects all candidates
- Preference: `text/html` → `text/plain` → first found

**`html_to_plain(html) → str`** — BeautifulSoup strip + whitespace normalization.

**`body_to_plain(mime_type, body) → str`** — routes to `html_to_plain` if `text/html`.

**`format_sent_date(msg) → str`** — converts `internalDate` (Unix ms) to `"YYYY-MM-DD HH:MM:SS UTC"`. Falls back to `Date` header, then `""`.

**`load_template(template_name, template_dir) → (subject, body)`**
- Tries `.html` first, then `.txt`
- File format: first line = subject, blank line, then body
- Raises `FileNotFoundError` if neither exists

**`send_email(creds, to_email, subject, body, images=None) → bool`**
- `images=None`: sends `MIMEText(body, "html")`
- `images` provided: sends `MIMEMultipart("related")` with inline images keyed by CID (`<img src="cid:KEY">`)
- Returns `True` on success, `False` on `HttpError`

---

### `docs.py`

Fetches email templates from a Google Doc via Drive API export.

**`fetch_template_from_doc(creds, doc_id, template_name) → (subject, body_html)`**

1. Exports the Google Doc as HTML via `drive.files().export(mimeType="text/html")`
2. Parses with BeautifulSoup
3. Splits body on `<h1>` elements — heading text = template name
4. Within the matched section: first non-empty paragraph = subject; remaining elements = body HTML

Raises `KeyError` if `template_name` not found, `ValueError` if section is empty.

**Doc format in Google Docs:**

```
[Heading 1]  tell_me_more_general
[Paragraph]  Subject line
[Paragraph]  Hi {name}, there's a charger near {address} in {city}, {state}.

[Heading 1]  waitlist
[Paragraph]  Subject line
[Paragraph]  Body content...
```

See `docs/email-template-guide.md` for full authoring instructions.

---

### `decision_tree.py`

Pure recursive evaluator. No I/O, no side effects.

**Node types:**

```yaml
# Branch:
condition:
  field: distance_miles   # driver_state | charger_state | charger_city | distance_miles
  op: lte                 # lt | lte | gt | gte | eq | ne | in
  value: 100
then: <node>
else: <node>

# Leaf:
template: waitlist        # string, or null for no-op
```

**`evaluate(node, context) → str | None`**

All string comparisons are case-insensitive. `in` operator accepts a list value.

**Context fields:**

| Field | Type | Source |
|-------|------|--------|
| `driver_state` | `str \| None` | `extract_state_from_address(address)` |
| `charger_state` | `str` | `charger_dict["state"]` |
| `charger_city` | `str` | `charger_dict["city"]` |
| `distance_miles` | `float` | `find_nearest_charger()` result |

> **YAML gotcha:** Use `then`/`else` — NOT `yes`/`no`. PyYAML parses bare `yes`/`no` as Python booleans, causing a runtime `KeyError`.

---

### `geo.py`

Geocoding and charger proximity. Uses Nominatim (OpenStreetMap) with a 1 req/sec rate limit.

**`geocode_address(address, cache_path=None) → (lat, lon) | None`**
- Strips apartment/unit designators before geocoding (so `"123 Main St Apt 4B"` and `"123 Main St Apt 12A"` share the same cache entry)
- Cache: JSON file mapping stripped address → `[lat, lon]`
- Returns `None` for unresolvable addresses

**`load_chargers(csv_path) → list[dict]`**
- `@cache` decorated — reads CSV at most once per process
- CSV columns: `STREET, CITY, STATE, ZIPCODE, CHARGERID, NUM_OF_CHARGERS, LAT, LONG, LAT_OVERRIDE, LONG_OVERRIDE`
- Uses `LAT_OVERRIDE`/`LONG_OVERRIDE` when non-empty
- Returns list of `{"name", "city", "state", "lat", "lon"}` dicts

**`find_nearest_charger(lat, lon, chargers) → (charger_dict, distance_miles) | None`**
- Uses `geopy.distance.geodesic` for great-circle distance
- Returns `None` if chargers list is empty

**`extract_state_from_address(address) → str | None`**
- Strategy 1: two-letter abbreviation at end of address
- Strategy 2: full state name mapped via 51-entry dict

**Bundled chargers (26 entries):**
Newburgh NY, Boston MA (×7), Brooklyn NY (×2), Detroit MI, San Francisco CA, Governors Island NY (×4), Portland ME, Los Angeles CA, Washington DC, Alameda CA — plus one Varennes QC (Canada).

---

### `sheets.py`

**`COLUMNS`** — 10 columns, A–J:

| Col | Header | Content |
|-----|--------|---------|
| A | Sent Date | `YYYY-MM-DD HH:MM:SS UTC` |
| B | Name | Extracted name |
| C | Address | Extracted address |
| D | Email 1 | Primary email |
| E | Email 2 | Form-submitted email |
| F | Content | Full body (truncated to `content_limit`) |
| G | Nearest Charger | `"STREET, CITY, STATE"` |
| H | Distance (mi) | Float as string |
| I | HubSpot Contact | `"created"` / `"failed"` / `""` |
| J | Email Sent | Template name / `"failed"` / `""` |

**Dedup logic — `row_hash(row, content_limit) → str`**

SHA-256 of:
- **Parsed rows**: `date + name + address + email_1 + email_2` (columns A–E)
- **Unparsed rows**: `date + truncated_content` (columns A + F)

HubSpot/email status columns are excluded — re-running with a different outcome does not create duplicate rows.

Header is prepended only if A1:J1 is empty.

---

### `hubspot.py`

**`upsert_contact(access_token, name, email, address) → str | None`**

- `POST https://api.hubapi.com/crm/v3/objects/contacts/batch/upsert`
- Dedup key: `idProperty="email"`
- Properties synced: `email`, `firstname`, `lastname`, `address`
- Name split on first space; single-word name → `lastname=""`
- Non-fatal: catches `requests.RequestException`, returns `None`
- Idempotent: re-running updates existing contact

---

### `cli.py`

Main entry point. Wires together all modules.

**Config resolution order:** CLI flags > `config.yaml` values > `_DEFAULTS`

**All config keys:**

| Key | Default | Purpose |
|-----|---------|---------|
| `label` | `"INBOX"` | Gmail label to read |
| `max_messages` | `100` | Max messages per run |
| `body_length` | `200` | Max body chars printed (0 = no limit) |
| `spreadsheet_id` | `""` | Google Sheet ID; empty = skip Sheets |
| `sheet` | `"Sheet1"` | Sheet tab name |
| `content_limit` | `5000` | Max chars in Content cell |
| `chargers` | bundled CSV | Path to chargers CSV |
| `geocache` | `"geocache.json"` | Path to geocache JSON |
| `fixture_dir` | `""` | Load emails from .txt files instead of Gmail |
| `hubspot_access_token` | `""` | HubSpot Private App token |
| `decision_tree_file` | `""` | Path to routing YAML |
| `template_dir` | `""` | Directory of local email templates |
| `google_doc_id` | `""` | Google Doc ID for templates (priority over `template_dir`) |

**Credential requirement:** Credentials are fetched when any of `spreadsheet_id`, `template_dir`, or `google_doc_id` is set. In pure fixture/preview mode they are skipped.

**Email send gate:** All of the following must be true:
- `decision_tree` loaded
- `nearest_charger_dict` found
- `dist_float` computed
- `parsed` succeeded
- `template_dir` or `google_doc_id` set
- `creds` available

**Body substitution:**
```python
body.format_map({
    "name":    parsed["name"],
    "address": parsed["address"],
    "city":    nearest_charger_dict["city"],
    "state":   ctx["driver_state"] or "",
})
```

---

### `gui.py` _(being replaced by web app)_

macOS CustomTkinter desktop app (560×660 px). Runs the pipeline in a background thread, streams `print()` output to a log widget via `_LogWriter` (thread-safe `after()` callback). Config loaded from a user-selected YAML file; `token.json`/`credentials.json` resolved relative to that file's directory.

**Known issues (not worth fixing — GUI is being replaced):**
1. Imports `get_template_images` from `gmail.py` — function no longer exists → `ImportError` at runtime
2. Body `format_map` only substitutes `{name}` and `{address}` — missing `{city}` and `{state}`
3. `google_doc_id` config key not supported

---

## Decision Tree Routes (`decision_tree.yaml`)

| Condition | Template |
|-----------|----------|
| `distance_miles <= 0.5` | `general_car_info` |
| `distance_miles > 100` | `waitlist` |
| Driver in `[CA, MA, DC, NY, MI]` AND CA charger AND city in `[Los Angeles, Alemeda]` AND `distance <= 10` | `tell_me_more_general` |
| Driver in `[CA, MA, DC, NY, MI]` AND CA charger AND city in `[Los Angeles, Alemeda]` AND `distance > 10` | `waitlist` |
| Driver in `[CA, MA, DC, NY, MI]` AND CA charger AND city `San Francisco` | `waitlist` |
| Driver in `[CA, MA, DC, NY, MI]` AND MA charger AND driver is MA | `tell_me_more_massachusetts` |
| Driver in `[CA, MA, DC, NY, MI]` AND MA charger AND driver is NOT MA | `waitlist` |
| Driver in `[CA, MA, DC, NY, MI]` AND DC charger | `tell_me_more_dc` |
| Driver in `[CA, MA, DC, NY, MI]` AND Brooklyn charger AND `distance <= 5` | `tell_me_more_brooklyn` |
| Driver in `[CA, MA, DC, NY, MI]` AND Newburgh charger AND `distance <= 10` | `tell_me_more_general` |
| Driver in `[CA, MA, DC, NY, MI]` AND MI charger AND `distance <= 10` | `tell_me_more_general` |
| Driver in `[CA, MA, DC, NY, MI]` AND in range but no match above | `waitlist` |
| Driver NOT in priority states (in range 0.5–100 mi) | `waitlist` |

**Template names used:** `general_car_info`, `tell_me_more_general`, `tell_me_more_massachusetts`, `tell_me_more_dc`, `tell_me_more_brooklyn`, `waitlist`

---

## Tests

### Coverage by file

| File | Count | What's covered |
|------|-------|----------------|
| `test_extract.py` | 4 | match, no-match, empty, None |
| `test_fixture.py` | 7 | body roundtrip, date, sort order, non-.txt filter, missing dir |
| `test_geo.py` | 24 | `_strip_unit` (9), `load_chargers`, `extract_state_from_address` (12), `find_nearest_charger` (4), `geocode_address` (4) |
| `test_gmail.py` | 23 | `get_body_from_payload` (8), `body_to_plain` (7), `format_sent_date` (5), `load_template` (6), `send_email` (6 incl. multipart/related) |
| `test_decision_tree.py` | 22 | all operators, nested tree, 17 real tree paths |
| `test_decision_tree_pipeline.py` | 7 | `_load_decision_tree`, `_build_tree_context` |
| `test_docs.py` | 10 | subject extraction, body HTML, multi-section, empty paragraphs, missing template, empty section, Drive API call |
| `test_sheets.py` | 12 | column structure, `row_hash` strategies, `truncate`, `append_rows` |
| `test_hubspot.py` | 5 | success, endpoint, name splitting, single-word name, request error |
| `test_integration.py` | 7 | full pipeline with fixture emails, geocache, charger CSV, routing |
| `test_gui_pipeline.py` | 12 | `_LogWriter`, completion guarantees, message/status outcomes |

### Strategy

- **No network calls in any test.** Nominatim mocked via `patch("itselectric.geo._geocode_fn")`. All Google APIs mocked via `unittest.mock.patch`.
- **Integration tests** use an inline geocache dict written to `tmp_path` + real bundled `chargers.csv`. Drive decision tree tested against the real `decision_tree.example.yaml`.
- **GUI tests** stub `customtkinter` via `sys.modules` injection before import; `_run_pipeline` tested by mocking all `itselectric.*` submodules.

### Fixture emails (integration test corpus)

| File | Address | Expected template |
|------|---------|-------------------|
| `01_parsed_contact.txt` | 19 Morris Ave, Brooklyn NY | `general_car_info` |
| `02_parsed_contact.txt` | 15 Washington St, Brooklyn NY | `general_car_info` |
| `03_unparsed_contact.txt` | _(plain question, no regex match)_ | unparsed |
| `04_ma_boston.txt` | 1 Cambridge St, Boston MA | `tell_me_more_massachusetts` |
| `05_dc_washington.txt` | 1100 16th St NW, Washington DC | `tell_me_more_dc` |
| `06_ca_losangeles.txt` | 123 N Vermont Ave, Los Angeles CA | `tell_me_more_general` |
| `07_ny_brooklyn.txt` | 1 Atlantic Ave, Brooklyn NY | `tell_me_more_brooklyn` |
| `08_mi_detroit.txt` | 1 Woodward Ave, Detroit MI | `tell_me_more_general` |
| `09_il_chicago.txt` | 100 N Michigan Ave, Chicago IL | `waitlist` (>100 mi) |
| `10_nj_hoboken.txt` | 100 Washington St, Hoboken NJ | `waitlist` (non-priority state) |

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `beautifulsoup4 >=4.12` | HTML parsing for body stripping and Docs template parsing |
| `geopy >=2.4` | Nominatim geocoder + geodesic distance |
| `google-api-python-client >=2.190` | Gmail, Sheets, Drive API clients |
| `google-auth >=2.48` | OAuth credential types |
| `google-auth-httplib2 >=0.3` | HTTP transport |
| `google-auth-oauthlib >=1.2.4` | `InstalledAppFlow` for desktop OAuth |
| `pyyaml >=6.0` | Config and decision tree YAML |
| `requests >=2.31` | HubSpot API HTTP calls |
| `customtkinter >=5.2` | Desktop GUI (being replaced) |

Dev extras: `pytest >=8.0`, `ruff >=0.4`, `pyinstaller >=6.0`, `types-PyYAML >=6.0`

Entry points: `itselectric` → `cli:main`, `itselectric-gui` → `gui:main`

Python requirement: `>=3.10`
