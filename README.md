# itselectric-automation

Web app that reads "It's Electric" contact-form emails from Gmail, extracts name/address/email fields, geocodes the address, finds the nearest EV charger, routes contacts to an email template via a configurable decision tree, and sends follow-up emails. Optionally creates/updates contacts in HubSpot CRM.

## What it does

1. **Fetch** — Reads Gmail messages by label, or loads local `.txt` fixtures for offline testing.
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

# 2. Add Google credentials (skip for fixture mode while auto-send is off)
#    Follow docs/google-auth.md, then save credentials.json in the repo root.

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
| `label` | Gmail label to read (e.g. `"Follow Up"`) |
| `max_messages` | Maximum messages to process per pipeline run |
| `hubspot_access_token` | HubSpot Private App token for CRM sync |
| `geocodio_api_key` | [Geocodio](https://geocod.io/) API key. Set to prefer Geocodio over the Nominatim fallback |
| `auto_send` | `true` to send emails automatically during pipeline runs |

For initial seeding, `config.yaml` (gitignored) is checked on startup; existing database values are not overwritten. See `config.example.yaml` for supported keys.

## Running tests

```bash
uv run --extra dev pytest tests/ -v       # Python tests (no network calls)
(cd web && npm test)                       # Vitest unit tests
(cd web && npx playwright test)            # E2E tests (server must be running)
```

## Docs

- [Repo overview](docs/repo-overview.md) — architecture, data flow, module reference
- [Configuration](docs/configuration.md) — all config keys, DB seeding, geocache
- [Google OAuth setup](docs/google-auth.md) — Gmail and optional Sheets authorization
- [HubSpot integration](docs/hubspot.md) — setup, what gets synced
- [Testing](docs/testing.md) — test suite, fixture emails, adding patterns
- [Email Template Guide](docs/email-template-guide.md) — authoring Markdown templates
- [Decision Tree Guide](http://localhost:8000/guide/decision-tree) — tree syntax and operators (after starting the app)
