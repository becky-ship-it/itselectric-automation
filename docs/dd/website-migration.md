# It's Electric — Web App Design Document

> Design Document · v0.2 · Decisions Incorporated

A locally-hosted, single-operator web tool for reading inbound EV inquiry emails, routing them through a decision tree, sending personalized responses, and tracking all outreach over time — replacing the current Python CLI and macOS desktop GUI.

| | |
|---|---|
| **Status** | Draft for Review |
| **Replaces** | `cli.py` · `gui.py` |
| **Backend** | Existing Python pipeline |
| **Audience** | It's Electric ops team |

---

## Contents

1. [Background & Goals](#1-background--goals)
2. [User Roles & Access](#2-user-roles--access)
3. [Core Features](#3-core-features)
4. [Pages & Navigation](#4-pages--navigation)
5. [Data Model](#5-data-model)
6. [Backend & Integration Architecture](#6-backend--integration-architecture)
7. [Migration from CLI/GUI](#7-migration-from-cligui)
8. [Decisions & Risks](#8-decisions--risks)

---

## 1. Background & Goals

### What the current system does

The existing `itselectric-automation` pipeline is a Python CLI (with a deprecated macOS GUI) that runs a full automated loop:

1. Pulls unread emails from a Gmail label (e.g. *Follow Up*)
2. Extracts structured data — name, address, email — via regex
3. Geocodes the address and finds the nearest EV charger from a bundled CSV
4. Evaluates the contact against a YAML decision tree to choose a response template
5. Sends a formatted HTML reply via Gmail
6. Logs the result to a Google Sheet and upserts the contact into HubSpot

This works, but requires someone to SSH into a machine or run a local binary. The macOS GUI is broken (import errors) and will not be maintained. A web app would make the tool accessible from anywhere without any local setup.

### Goals for the web app

- **Visibility.** Show what the pipeline is doing in real time and give operators a clear log of every email sent.
- **Control.** Let operators review and approve sends before they go out, or switch to fully automatic mode.
- **Configuration.** Manage the decision tree, email templates, and charger data through the UI rather than editing YAML files.
- **History.** Provide a persistent, searchable record of all processed contacts and sent emails.
- **Reliability.** Avoid the fragility of the local setup — OAuth token management, machine availability, manual runs.

> **Scope boundary:** This document covers the web frontend and its integration contract with the existing Python backend modules. It does not redesign the decision tree logic, geocoding, or Gmail API calls — those are preserved as-is.

### What the web app does *not* change

- The regex extraction logic in `extract.py`
- The decision tree evaluator in `decision_tree.py`
- The Gmail API send/receive code in `gmail.py`
- The HubSpot upsert logic in `hubspot.py`
- The Google Sheets dedup + append in `sheets.py`
- The geocoding and charger proximity logic in `geo.py`

---

## 2. User Roles & Access

V1 is a single-operator tool running locally on one machine. There is no login screen, no session management, and no multi-user access control. The app is accessed by opening `localhost:8000` in a browser while the server is running. Anyone with access to the machine can use it.

Multi-user access, a dedicated hosted deployment, and a shared database are explicitly out of scope for v1 and will be designed separately for v2.

| Role | Can do | V1? |
|---|---|---|
| Operator (local) | Run pipeline, review/send emails, view history, edit decision tree and templates, export/import DB snapshot | Yes — single implicit user, no login |
| Viewer | Read-only access to history and dashboard | No (v2) |
| Multi-user / hosted | Shared DB, user accounts, role-based access | No (v2) |

> **Auth simplification:** Because v1 is local-only, no auth layer is needed. The existing `InstalledAppFlow.run_local_server()` in `auth.py` already works correctly when the server runs on the same machine as the browser — the OAuth redirect lands on `localhost` without any changes. Token storage stays as `token.json` on disk. No DB migration for credentials is needed in v1.

---

## 3. Core Features

### 3.1 Email inbox review

The app fetches emails from the configured Gmail label and presents them in a list. Each email shows: sender name, address, date received, parse status (parsed / unparsed), and the routing decision the decision tree produced.

From this view the operator can see at a glance which emails are ready to send, which failed to parse, and which have already been processed.

#### Email states

| State | Meaning | Action available |
|---|---|---|
| Pending | Parsed, template resolved, not yet sent | Preview, Send, Skip |
| Needs attention | Parsed but geocode failed — no nearest charger found | Edit address, retry geocode, force-send with manual template |
| Unparsed | Email body didn't match extraction regex | View raw, Mark as skipped |
| No route | Parsed but decision tree returned null | View details, force-send with chosen template |
| Sent | Response email delivered | View sent copy |
| Skipped | Manually skipped by operator | Undo skip |
| Failed | Gmail send returned an error | Retry, view error |

### 3.2 Email preview & send

Before sending, the operator sees a preview of the rendered email — with the recipient's name, address, and nearest charger already interpolated. The preview is shown alongside the metadata: recipient address, distance to nearest charger, and the template that was selected.

The operator can change the template manually before sending if the routed template seems wrong. Sending is a single button click.

> **Auto-send mode:** A toggle lets operators enable fully automatic sending: once the pipeline runs and resolves a template, the email is sent without manual review. This matches the current CLI behavior. Manual review mode is the safer default for the MVP launch.

### 3.3 Pipeline run control

A "Run pipeline" button triggers the backend to fetch emails from Gmail, parse them, geocode addresses, and resolve templates — all without sending. The operator then reviews the results. An optional "Run & send all" shortcut skips review when auto-send mode is on.

The UI streams pipeline progress in real time: which email is being processed, any geocoding errors, any decision tree misses. This replaces the `_LogWriter` thread in the old GUI.

### 3.4 History, export & import

Every processed email — sent, skipped, or failed — is recorded in a persistent local SQLite database. The history page provides a searchable log of all contacts and sent emails. Because the tool runs locally, sharing data with others (or migrating to a new machine) requires a dedicated export/import mechanism.

#### Export

A "Download snapshot" button on the History page exports the full database as a single portable file. Two formats are offered:

- **JSON snapshot** — the canonical portable format. Includes all tables (contacts, outbound_emails, chargers, templates, geocache). Anyone can import this into their own local setup.
- **CSV export** — a flat spreadsheet of `outbound_emails` joined with `contacts`, matching the existing Google Sheets column layout. For sharing with people who don't run the tool.

#### Import

An "Upload snapshot" option on the History page accepts a JSON snapshot file from another instance. The import is **merge-based**, not destructive: rows are upserted by their natural keys (Gmail message ID for contacts, template name for templates) so running an import twice is safe. Charger data and geocache entries are merged the same way. The operator sees a preview of what will change before confirming.

> **Google Sheets — kept as a parallel output:** Sheets append continues to run as a background task after each send, exactly as today. This preserves the existing log and means collaborators who rely on the sheet see new entries in near-real-time without needing to import a snapshot. The local DB is the source of truth; the sheet is a derived view.

### 3.5 Decision tree editor

The current `decision_tree.yaml` is edited by hand in a text editor. The web app provides a dual-mode editor — operators can switch between a **visual editor** and a **YAML editor** at any time, with both views staying in sync.

#### Visual editor

A tree view of conditions and leaf outcomes, rendered as an expandable node hierarchy. Each condition node shows its field, operator, and value in a small form (e.g. "distance_miles ≤ 100"). Each leaf shows the template it routes to, or "no-op" if null. Operators can add, remove, and reorder nodes by clicking, without touching any YAML.

#### YAML editor

A full-width code editor (e.g. CodeMirror) showing the raw YAML, with syntax highlighting and real-time parse validation. Operators who prefer working directly in YAML can do so. Switching back to the visual editor after a YAML edit re-parses and re-renders the tree immediately. Parse errors are shown inline and block saving.

#### Dry-run validation

Before saving any change (from either editor), the app runs the updated tree against the 10 fixture emails and displays a before/after routing table. If any fixture's route has changed, the changed rows are highlighted. The operator must explicitly confirm before the new tree is saved.

### 3.6 Template management

Email templates are currently stored either as local `.html/.txt` files or in a Google Doc. The web app provides a template list showing all templates by name, with a live preview that renders the template with placeholder values. Operators can edit template subject lines and body copy directly in the app. Templates are stored in the app's own database, with an option to sync back to the Google Doc.

### 3.7 Charger map

A read-only map view of the 26 bundled EV charger locations, with the ability to add or remove entries. Charger data is stored in the app database (initialized from `chargers.csv`) and exported as a new CSV when changed. The existing `find_nearest_charger()` logic continues to work without modification.

---

## 4. Pages & Navigation

The app has five main pages, accessible from a persistent left sidebar.

### `/` — Dashboard

Summary of recent pipeline activity.

- Count of pending, sent, skipped emails
- "Run pipeline" button + last-run timestamp
- Recent activity feed (last 10 processed)
- Quick-action: "Run & send all pending"

### `/inbox` — Inbox

List of emails fetched from Gmail.

- Filter by state (pending / sent / unparsed / needs attention…)
- Click row → email detail + preview panel
- Bulk select → send selected
- Inline template override before send

### `/history` — History

Persistent log of all processed contacts.

- Search by name, address, email, template
- Date range filter
- Download snapshot (JSON or CSV)
- Upload snapshot to merge another instance's data
- Click row → contact detail

### `/config` — Configuration

All pipeline settings in one place.

- Gmail label, max messages, auto-send toggle
- Decision tree: visual editor ↔ YAML editor toggle
- Template editor (list + rich text)
- Charger table editor

### `/inbox/:id` — Email detail

Shows: raw email body, extracted fields, nearest charger, decision tree trace (which conditions matched), rendered preview of outbound email, and send/skip/override controls. Accessible as a slide-over panel or dedicated page.

### Navigation structure

Left sidebar with five items: Dashboard, Inbox, History, Configuration, and a bottom-pinned Settings (credentials, auto-send toggle). A persistent run-status strip at the top shows when the pipeline is running and streams its progress.

### Key interaction: inbox → send flow

```
Run pipeline → Review inbox → Preview email → Send → Logged
(fetch+parse)  (pending list)  (verify template)  (Gmail API)  (DB + Sheets + HubSpot)
```

---

## 5. Data Model

The app uses SQLite via SQLAlchemy. Single file on disk, zero config, perfect for local single-user use. PostgreSQL can be swapped in for a v2 hosted deployment.

### `contacts` — one row per inbound inquiry email

| Column | Type | Notes |
|---|---|---|
| `id` | text PK | Gmail message ID as natural key |
| `received_at` | datetime | From Gmail `internalDate` |
| `name` | text | Extracted via regex; null if unparsed |
| `address` | text | Full address string |
| `email_primary` | text | Email 1 from form |
| `email_form` | text | Email 2 (form-submitted) |
| `raw_body` | text | Stripped plain-text body |
| `parse_status` | enum | `parsed` / `unparsed` |
| `nearest_charger_id` | FK → chargers | Null if geocode failed |
| `distance_miles` | float | |
| `geocache_hit` | bool | Was the address already cached? |
| `hubspot_status` | enum | `created` / `updated` / `failed` / `skipped` |

### `outbound_emails` — one row per send attempt

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `contact_id` | FK → contacts | |
| `template_name` | text | Which template was used |
| `routed_template` | text | What the decision tree originally chose (may differ if operator overrode) |
| `subject` | text | Final subject after interpolation |
| `body_html` | text | Final rendered body |
| `sent_at` | datetime | Null if not yet sent |
| `status` | enum | `pending` / `sent` / `failed` / `skipped` |
| `sent_by` | text | `"auto"` or operator identifier for audit trail |
| `error_message` | text | Gmail API error if status = failed |

### `chargers` — initialized from `chargers.csv`; editable via UI

| Column | Type |
|---|---|
| `id` | integer PK |
| `street`, `city`, `state`, `zipcode` | text |
| `charger_id` | text (original CSV identifier) |
| `num_chargers` | int |
| `lat`, `lon` | float (from `LAT_OVERRIDE`/`LONG_OVERRIDE` if set) |

### `templates` — replaces local `.html` files and Google Doc

| Column | Type |
|---|---|
| `name` | text PK (e.g. `tell_me_more_dc`) |
| `subject` | text |
| `body_html` | text |
| `updated_at` | datetime |

> **Geocache:** The existing `geocache.json` file (address → lat/lon) is imported into a `geocache` table (address text, lat float, lon float) in the same SQLite database. `geo.py` will need a small adapter to read/write from the database instead of the JSON file, or the JSON file can be kept and hydrated from the DB on startup.

---

## 6. Backend & Integration Architecture

### Recommended stack

Because v1 runs locally on a single machine, the stack is as simple as possible — no deployment infrastructure, no remote auth, no reverse proxy needed.

| Layer | Recommendation | Rationale |
|---|---|---|
| Web framework | FastAPI | Async-friendly, easy background tasks for geocoding and HubSpot calls, auto-generates OpenAPI docs |
| Database | SQLite (via SQLAlchemy) | Single file on disk, zero config, perfect for local single-user use. Swap to Postgres for v2. |
| Frontend | React + Vite | Component model handles the SSE-streamed log well; fast HMR during development |
| Real-time | Server-Sent Events (SSE) | Simpler than WebSockets for one-way pipeline progress stream; works natively in browsers |
| Auth | None (v1) | Local-only — anyone at `localhost:8000` is the operator. Google OAuth handled by existing `auth.py` unchanged. |
| Deployment | Local process (`uvicorn main:app`) | Started from the terminal; browser opens to localhost. No server, no Docker, no cloud needed for v1. |

### API design — key endpoints

#### Pipeline

| Endpoint | Description |
|---|---|
| `POST /api/pipeline/run` | Fetch + parse emails, geocode, resolve templates. Returns run ID. |
| `GET /api/pipeline/stream` | SSE stream of log lines while pipeline is running |
| `GET /api/pipeline/status` | Current run status (idle / running / last_run_at) |

#### Inbox / Contacts

| Endpoint | Description |
|---|---|
| `GET /api/contacts` | List contacts; filter by status, date range |
| `GET /api/contacts/:id` | Single contact detail + associated outbound email(s) |
| `POST /api/contacts/:id/send` | Send the pending email for this contact (optionally with template override) |
| `POST /api/contacts/:id/skip` | Mark as skipped |
| `POST /api/contacts/send-batch` | Send all pending emails |

#### Configuration

| Endpoint | Description |
|---|---|
| `GET/PUT /api/config` | App-level settings (label, max_messages, auto_send, etc.) |
| `GET/PUT /api/decision-tree` | Get or update the full decision tree JSON |
| `POST /api/decision-tree/test` | Dry-run tree against fixture emails; returns routing table |
| `GET/POST/PUT/DELETE /api/templates` | CRUD for email templates |
| `GET/POST/PUT/DELETE /api/chargers` | CRUD for charger locations |

#### Export & Import

| Endpoint | Description |
|---|---|
| `GET /api/export/snapshot` | Download full DB as a JSON snapshot (contacts, outbound_emails, templates, chargers, geocache) |
| `GET /api/export/csv` | Download flat CSV in Google Sheets column format |
| `POST /api/import/snapshot` | Upload and merge a JSON snapshot; returns a preview diff before committing |
| `POST /api/import/snapshot/confirm` | Commit a previewed import after operator review |

### How the existing Python modules integrate

Each module becomes a service-layer dependency of the FastAPI app. No module needs to be rewritten — only their I/O is redirected from files/stdout to the database and the API response stream.

| Module | Change needed |
|---|---|
| `auth.py` | **None for v1.** `InstalledAppFlow.run_local_server()` already works when the browser is on the same machine. `token.json` stays on disk as-is. |
| `extract.py` | None — pure functions, no I/O. |
| `geo.py` | Cache reads/writes from `geocache` DB table instead of `geocache.json`. Charger list loaded from `chargers` DB table. Geocode failures write a `needs_attention` status to the contact row. |
| `gmail.py` | None for fetch/send. `load_template` replaced by DB lookup. |
| `docs.py` | Optional — keep for initial template import from Google Doc; templates live in DB going forward. |
| `decision_tree.py` | None — pure function. Tree loaded from DB as dict instead of YAML file. |
| `sheets.py` | Keep as-is. App logs to DB first, then fires Sheets append as a background task after each send. |
| `hubspot.py` | None — called as a background task; result stored in `contacts.hubspot_status`. |
| `cli.py` | Replaced by `POST /api/pipeline/run`. Keep file for emergency local use. |
| `gui.py` | Retired. Not migrated. |
| `fixture.py` | Kept for testing. Exposed via a dev-only `POST /api/pipeline/run?fixture=true` flag. |

> **OAuth unchanged in v1:** Because the app runs locally, `auth.py` requires zero changes. `InstalledAppFlow.run_local_server()` opens a browser tab on the same machine, the OAuth redirect lands on `localhost`, and `token.json` is written to disk exactly as it is today. The "server OAuth callback" approach is only needed when the server and browser are on different machines — that's a v2 concern.

---

## 7. Migration from CLI/GUI

### What to keep

| Component | Status |
|---|---|
| All `src/itselectric/` modules (except `gui.py`) | Keep as-is |
| All tests in `tests/` | Keep — add API-layer tests |
| `decision_tree.yaml` | Migrate → DB |
| `config.yaml` | Migrate → DB / env vars |
| `geocache.json` | Migrate → DB table |
| `chargers.csv` | Migrate → DB table |
| Email templates (local files or Google Doc) | Migrate → DB table |
| `gui.py` | Retire |
| `cli.py` | Keep for local use / emergency fallback |
| `app.spec`, `build_app.sh` | Retire |

### Suggested build order

1. **Phase 1 — Backend skeleton.** FastAPI app with SQLite, DB schema, import scripts for `chargers.csv` / `decision_tree.yaml` / existing templates / `geocache.json`, and the core pipeline endpoint wired to the existing Python modules. `auth.py` untouched.
2. **Phase 2 — Inbox UI.** React frontend: dashboard, inbox list, email detail + preview, send/skip actions. SSE-streamed pipeline progress log. Needs-attention queue for geocode failures.
3. **Phase 3 — History, export & import.** History page with search, JSON snapshot export, CSV export, and merge-import from another instance.
4. **Phase 4 — Configuration UI.** Decision tree dual editor (visual + YAML, with fixture dry-run diff), template editor, charger table editor.
5. **Phase 5 — Polish.** Auto-send mode, startup script (one command to launch), credential health indicator on dashboard.

> **Backwards compatibility during build:** The Google Sheets append continues running as a background task throughout all phases. The CLI continues to work against the original YAML config files during Phase 1, giving a safe fallback if the web UI has issues. Both can be used in parallel indefinitely — nothing forces a cutover.

---

## 8. Decisions & Risks

### Decisions made

The following questions from the initial draft have been answered and are incorporated into this document.

| Question | Decision | Implications |
|---|---|---|
| Single operator or multi-user? | Single operator, v1 only | No auth layer. No login screen. App runs on `localhost`. Multi-user is v2. |
| Scheduled pipeline or operator-triggered? | Always operator-triggered | No cron, no APScheduler, no background scheduler needed. "Run pipeline" button is the only trigger. |
| Google Sheets — keep or replace? | Keep as parallel output | Sheets append fires as a background task after each send. Local SQLite DB is the primary store. Export/import handles data sharing between instances. |
| Decision tree editor — visual only or also YAML? | Both, switchable in-place | Visual editor and YAML editor share the same underlying data. A tab or toggle switches between them. Both are in sync at all times. |
| What happens when geocoding fails? | "Needs attention" state | Geocode failures surface as a distinct inbox state. Operator can edit the address and retry, or force-send with a manually chosen template. |
| Geocoder — Nominatim or Google Maps? | Nominatim (unchanged) | No change to `geo.py`. The SSE progress log makes slow geocoding batches visible rather than mysterious. |

### Open question — v2 data portability

The JSON snapshot export/import described in section 3.4 covers the "share data between two local instances" use case. When v2 introduces a hosted deployment with a shared database, a migration path will be needed from the local SQLite files to the hosted DB. This is not in scope for v1 but should be kept in mind when designing the export schema — the JSON format should be stable enough that v2's import tool can consume v1 snapshots without a conversion step.

### Risks

**Nominatim rate limiting during large batches**

Nominatim enforces 1 req/sec. A run with many new addresses can take several minutes. The SSE progress stream makes this visible, but a very long run could feel broken. The geocache means each address is only fetched once ever, so in practice batches of truly new addresses are small. If this becomes a problem, add a progress bar with an estimated time remaining.

**Decision tree regressions**

A well-intentioned edit — adjusting a distance threshold, adding a state — can silently reroute a large class of contacts to the wrong template. The fixture dry-run diff on save is the primary mitigant. Consider also storing a timestamped history of decision tree versions in the DB so a bad edit can be rolled back without digging through version control.

**Token expiry between runs**

If the operator doesn't run the pipeline for several days, the Google OAuth refresh token may expire or be revoked. `auth.py` handles this by deleting `token.json` and triggering a fresh browser login — but silently, from the CLI. The web app should surface this clearly: a "Google credentials expired — click to re-authenticate" banner on the dashboard, triggered whenever a pipeline run fails with a `RefreshError`.

---

*v0.2 — all original open questions resolved. Remaining items are v2 planning notes and known risks, not blockers for build.*