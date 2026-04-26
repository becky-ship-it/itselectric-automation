# itselectric-automation

Web app that reads "It's Electric" contact-form emails from Gmail, extracts name/address/email fields, geocodes the address, finds the nearest EV charger, routes contacts to an email template via a configurable decision tree, and sends follow-up emails. Optionally creates/updates contacts in HubSpot CRM.

## What it does

1. **Fetch** — Reads Gmail messages by label, or loads `.txt` files locally (no auth required for testing).
2. **Extract** — Pulls out name, address, and email addresses via regex.
3. **Geocode** — Converts the address to lat/long using Nominatim (cached in DB to avoid repeat calls).
4. **Proximity** — Finds the nearest EV charger from a bundled CSV.
5. **Route** — Evaluates a configurable decision tree to select an email template.
6. **Send** — Sends a personalized follow-up email via Gmail (manual or auto).
7. **HubSpot** *(optional)* — Creates or updates a CRM contact. Deduplicates by email.

## Setup

**Requirements:** Python 3.10+, Node.js 18+, `uv` ([install](https://astral.sh/uv))

```bash
# 1. Clone and start the server (installs all deps + builds frontend automatically)
./run_server.sh

# 2. Add Google credentials (skip if using fixture mode only)
#    Download OAuth 2.0 Desktop credentials from Google Cloud Console
#    and save as credentials.json in the repo root.

# 3. Open http://localhost:8000
```

## Auto-start on Mac login

```bash
./install_service.sh
```

This registers the server as a macOS LaunchAgent so it starts automatically on login and restarts if it crashes. Logs go to `~/Library/Logs/itselectric-server.log`.

To stop/start manually:
```bash
launchctl unload ~/Library/LaunchAgents/com.itselectric.server.plist
launchctl load ~/Library/LaunchAgents/com.itselectric.server.plist
```

## Configuration

All settings are managed through the web UI at `/config`. No config file editing required after initial setup.

Key settings:

| Setting | Purpose |
|---------|---------|
| `gmail_label` | Gmail label to read (e.g. `"Follow Up"`) |
| `hubspot_access_token` | HubSpot Private App token for CRM sync |
| `auto_send` | `true` to send emails automatically during pipeline runs |
| `google_doc_id` | Google Doc ID for email templates (takes priority over built-in templates) |

For initial seeding, `config.yaml` (gitignored) is read once on server startup. See `config.example.yaml` for all keys.

## Running tests

```bash
uv run pytest tests/ -v    # 207 Python tests (no network calls)
cd web && npm test          # Vitest unit tests
cd web && npx playwright test  # E2E tests (server must be running)
```

## Docs

- [Repo overview](docs/repo-overview.md) — architecture, data flow, module reference
- [Configuration](docs/configuration.md) — all config keys, DB seeding, geocache
- [HubSpot integration](docs/hubspot.md) — setup, what gets synced
- [Testing](docs/testing.md) — test suite, fixture emails, adding patterns
- [Email Template Guide](/guide/templates) — authoring templates (served by the app)
- [Decision Tree Guide](/guide/decision-tree) — tree syntax and operators (served by the app)
