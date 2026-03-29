# itselectric-automation

Reads "It's Electric" contact-form emails from Gmail, extracts structured fields, geocodes the address, finds the nearest EV charger, writes rows to a Google Sheet, and optionally creates/updates contacts in HubSpot CRM.

## What it does

1. **Fetch** — Reads Gmail messages by label, or loads `.txt` files locally (no auth required).
2. **Extract** — Pulls out name, address, and email addresses via regex.
3. **Geocode** — Converts the address to lat/long using Nominatim (cached to avoid repeat calls).
4. **Proximity** — Finds the nearest EV charger from a bundled CSV.
5. **Sheets** *(optional)* — Appends rows to a Google Sheet. Deduplicates on re-run.
6. **HubSpot** *(optional)* — Creates or updates a CRM contact. Deduplicates by email.

## Setup

```bash
# 1. Install dependencies
uv sync --extra dev

# 2. Add Google credentials (skip if using fixture mode)
#    Download OAuth 2.0 Desktop credentials from Google Cloud Console
#    and save as credentials.json in the repo root.

# 3. Create config
cp config.example.yaml config.yaml
#    Edit config.yaml with your spreadsheet ID, labels, tokens, etc.
```

See [docs/configuration.md](docs/configuration.md) for all config options.

## Running

```bash
uv run itselectric                                    # uses config.yaml
uv run itselectric --fixture-dir tests/fixtures/emails  # no credentials needed
uv run itselectric-gui                                # desktop GUI
./build_app.sh                                        # build macOS .app
```

## Docs

- [Configuration](docs/configuration.md) — all config keys, geocache, chargers CSV format
- [HubSpot integration](docs/hubspot.md) — setup, what gets synced, behaviour
- [Testing](docs/testing.md) — running tests, fixture emails, adding extraction patterns
