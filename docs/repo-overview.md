# Repo Overview: itselectric-automation

FastAPI + React web app that reads "It's Electric" EV contact-form emails from Gmail, extracts structured fields via regex, geocodes the address, finds the nearest charger, routes to an email template via a configurable decision tree, sends follow-up emails, and optionally upserts contacts into HubSpot CRM.

---

## Repository Layout

```
/
├── src/itselectric/              # Core pipeline library (Python)
│   ├── auth.py                   # Google OAuth credential management
│   ├── decision_tree.py          # Decision tree evaluator
│   ├── email_layout.py           # HTML email wrapper (logo header + footer)
│   ├── extract.py                # Regex extraction from email bodies
│   ├── fixture.py                # Local .txt email source for dev/testing
│   ├── geo.py                    # Geocoding (Nominatim) + charger proximity
│   ├── gmail.py                  # Gmail API: fetch, decode, send, load templates
│   ├── hubspot.py                # HubSpot CRM: upsert contacts
│   ├── sheets.py                 # Google Sheets API: dedup + append (legacy)
│   └── data/
│       └── chargers.csv          # Bundled EV charger locations (26 entries)
│
├── server/                       # FastAPI application
│   ├── main.py                   # App entry point, DB init, seeding, static file serving
│   ├── db.py                     # SQLAlchemy engine + session helpers
│   ├── models.py                 # ORM models (Contact, OutboundEmail, AppConfig, ...)
│   ├── schemas.py                # Pydantic request/response schemas
│   ├── pipeline_service.py       # Core pipeline logic (fetch → extract → geo → route → send)
│   ├── seed.py                   # DB seeding: chargers, geocache, decision tree, config, templates
│   ├── log_store.py              # In-process log buffer (SSE-streamed to frontend)
│   ├── sse.py                    # Server-Sent Events helper
│   └── routers/
│       ├── pipeline.py           # POST /api/pipeline/run, /api/pipeline/run-fixtures
│       ├── contacts.py           # CRUD + send + fix for contacts
│       ├── templates.py          # Email template CRUD
│       ├── config.py             # App config key/value store
│       ├── chargers.py           # Charger list read-only endpoint
│       ├── export.py             # CSV + JSON export
│       └── logs.py               # SSE log stream
│
├── web/                          # React frontend (Vite + TypeScript + Tailwind)
│   ├── src/
│   │   ├── App.tsx               # Router setup (React Router v7)
│   │   ├── api/client.ts         # Typed API client (all fetch calls)
│   │   ├── components/           # Shared components (Sidebar, ContactRow, TreeNodeEditor)
│   │   └── pages/
│   │       ├── Dashboard.tsx     # Pipeline run controls + status counts
│   │       ├── Inbox.tsx         # Contact list (All / Pending / Unparsed tabs)
│   │       ├── InboxDetail.tsx   # Contact detail + email preview + send/fix
│   │       ├── History.tsx       # All contacts table + search + CSV/JSON export
│   │       ├── Config.tsx        # Email templates + decision tree editor
│   │       ├── Logs.tsx          # Live SSE log stream
│   │       ├── TemplateGuide.tsx # Email template authoring guide
│   │       └── DecisionTreeGuide.tsx  # Decision tree syntax guide
│   ├── e2e/app.spec.ts           # Playwright E2E tests (18 tests)
│   └── playwright.config.ts
│
├── tests/                        # Python test suite (207 tests)
│   ├── fixtures/emails/          # 11 .txt fixture files for offline pipeline tests
│   ├── test_api_*.py             # FastAPI endpoint tests (contacts, config, pipeline, ...)
│   ├── test_decision_tree.py
│   ├── test_email_layout.py
│   ├── test_extract.py
│   ├── test_fixture.py
│   ├── test_geo.py
│   ├── test_gmail.py
│   ├── test_hubspot.py
│   ├── test_integration.py
│   ├── test_models.py
│   ├── test_pipeline_service.py
│   ├── test_seed.py
│   └── test_sheets.py
│
├── data/                         # Runtime DB (gitignored)
│   └── itselectric.db            # SQLite database
│
├── config.example.yaml           # Seed config template
├── decision_tree.yaml            # Seed-only decision tree (DB is live source after first run)
├── decision_tree.example.yaml    # Example tree for integration tests
├── run_server.sh                 # Start script (installs deps + builds frontend + starts uvicorn)
├── install_service.sh            # macOS LaunchAgent installer
└── pyproject.toml
```

---

## End-to-End Data Flow

### Pipeline run (`POST /api/pipeline/run` or `POST /api/pipeline/run-fixtures`)

```
Gmail label  OR  tests/fixtures/emails/*.txt
  ↓  fetch_messages() / load_fixture_messages() → list of Gmail-shaped message dicts

Per message:
  ↓  get_body_from_payload() → (mime_type, raw_text)
  ↓  body_to_plain()         → stripped plain text
  ↓  extract_parsed()        → {"name", "address", "email_1", "email_2"} or None

  → Upsert Contact row in DB (parse_status = "parsed" | "unparsed")

If parsed:
  ↓  upsert_contact()        → HubSpot CRM (if hubspot_access_token configured)
  ↓  geocode_address()       → (lat, lon) via Nominatim, cached in GeoCache table
  ↓  find_nearest_charger()  → (charger_dict, distance_miles)
  ↓  evaluate(tree, ctx)     → template_name

  ↓  load template body from DB (EmailTemplate table)
  ↓  body.format_map(SafeDict(name, address, city, state))
  ↓  render_email(body)      → HTML email via email_layout.py

  → Upsert OutboundEmail row in DB (status = "pending")

  If auto_send = true:
    ↓  send_email() → Gmail API
    → Update OutboundEmail status = "sent" | "failed"
```

### Contact fix (`POST /api/contacts/{id}/fix`)

User manually corrects name/email/address for an unparsed contact via the Inbox UI. The fix endpoint re-runs geocoding, charger lookup, tree evaluation, and creates/replaces the outbound email.

---

## Server Modules

### `server/main.py`

Configures FastAPI, runs DB migrations (`Base.metadata.create_all`), and seeds initial data on startup:
- **`seed_chargers`** — loads `src/itselectric/data/chargers.csv` into `Charger` table (idempotent)
- **`seed_geocache`** — loads `geocache.json` into `GeoCache` table if it exists (one-time import)
- **`seed_decision_tree_from_yaml`** — loads `decision_tree.yaml` into `DecisionTreeNode` table (skips if already seeded)
- **`seed_templates_from_yaml`** — loads template names from `decision_tree.yaml` leaf nodes into `EmailTemplate` table (skips existing)
- **`seed_config`** — loads `config.yaml` values into `AppConfig` table (skips existing keys)

Serves the built React frontend from `web/dist/` as static files, with SPA fallback.

### `server/pipeline_service.py`

Core logic called by the pipeline router. Key behaviors:
- Uses `_SafeDict` for template variable substitution — unknown `{variables}` are left as-is instead of throwing `KeyError`
- Reads the decision tree from DB (`DecisionTreeNode` table) as a dict at runtime
- Reads config from `AppConfig` table (e.g. `gmail_label`, `auto_send`, `hubspot_access_token`)
- Creates/updates `Contact` and `OutboundEmail` rows atomically per message

### `server/models.py`

| Model | Purpose |
|-------|---------|
| `Contact` | One row per incoming email: name, address, emails, parse status, hubspot status |
| `OutboundEmail` | One per routed contact: template, body, status (pending/sent/failed/skipped), sent_at |
| `EmailTemplate` | Key/value store of template name → (subject, body) pairs |
| `DecisionTreeNode` | Serialized tree structure (parent/child IDs, condition fields) |
| `AppConfig` | Key/value config store (replaces config.yaml at runtime) |
| `Charger` | EV charger locations (seeded from CSV) |
| `GeoCache` | Address → lat/lon cache (seeded from geocache.json) |

---

## Core Library Modules (`src/itselectric/`)

### `extract.py`

**`extract_parsed(content: str) → dict | None`**

Matches the specific text format of "It's Electric" contact form emails:

```
it's electric <Name> The user has an address of <Address> and has an email of
<email_1>
Email address submitted in form
<email_2>
```

Returns `{"name", "address", "email_1", "email_2"}` on match, `None` otherwise.

### `geo.py`

**`geocode_address(address, cache_path=None) → (lat, lon) | None`** — Nominatim lookup with JSON file cache. Strips unit designators before geocoding.

**`load_chargers() → list[dict]`** — `@cache`-decorated, reads bundled CSV once per process.

**`find_nearest_charger(lat, lon, chargers) → (charger_dict, distance_miles) | None`** — geodesic distance via geopy.

**`extract_state_from_address(address) → str | None`** — two-letter abbreviation or full state name.

**`parse_address_components(address) → dict`** — splits `"Street, City, ST 12345"` into `{street, city, state, zip}` for HubSpot.

### `hubspot.py`

**`upsert_contact(access_token, name, email, address) → str | None`**

- `POST https://api.hubapi.com/crm/v3/objects/contacts/batch/upsert`
- Dedup key: `idProperty="email"`
- Properties: `email`, `firstname`, `lastname`, `address` (street), `city`, `state`, `zip`, `form_selection: "EV Driver"`
- Non-fatal: catches `RequestException`, returns `None`

### `gmail.py`

**`send_email(creds, to_email, subject, body) → bool`** — sends HTML email via Gmail API.

**`fetch_messages(creds, label, max_messages) → list[dict]`** — reads Gmail by label.

**`get_body_from_payload / body_to_plain / format_sent_date`** — message decoding helpers.

### `email_layout.py`

**`render_email(body_html: str) → str`** — wraps body in branded HTML email: white background, It's Electric logo header, footer with unsubscribe copy.

### `decision_tree.py`

**`evaluate(node, context) → str | None`** — pure recursive evaluator.

Node types: `condition` (branch with `field`, `op`, `value`, `then`, `else`) or `template` (leaf).

Operators: `lt`, `lte`, `gt`, `gte`, `eq`, `ne`, `in`. String comparisons case-insensitive.

Context fields: `driver_state`, `charger_state`, `charger_city`, `distance_miles`.

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/pipeline/run` | Run pipeline against Gmail |
| `POST` | `/api/pipeline/run-fixtures` | Run pipeline against fixture files |
| `GET` | `/api/contacts` | List contacts (filterable by status) |
| `GET` | `/api/contacts/{id}` | Get contact + email preview |
| `POST` | `/api/contacts/{id}/send` | Send outbound email manually |
| `POST` | `/api/contacts/{id}/fix` | Fix unparsed contact fields + re-route |
| `POST` | `/api/contacts/send-batch` | Send all pending emails |
| `GET` | `/api/templates` | List email templates |
| `GET` | `/api/templates/{name}` | Get template body |
| `PUT` | `/api/templates/{name}` | Save template body |
| `GET` | `/api/config` | Get all config key/value pairs |
| `PUT` | `/api/config/{key}` | Set config value |
| `GET` | `/api/chargers` | List charger locations |
| `GET` | `/api/export/csv` | Download contacts as CSV |
| `GET` | `/api/export/json` | Download contacts as JSON |
| `GET` | `/api/logs/stream` | SSE log stream |

---

## Bundled Chargers (26 entries)

Newburgh NY, Boston MA (×7), Brooklyn NY (×2), Detroit MI, San Francisco CA, Governors Island NY (×4), Portland ME, Los Angeles CA, Washington DC, Alameda CA, Varennes QC.
