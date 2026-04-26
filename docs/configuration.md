# Configuration

All settings are stored in the database and managed through the web UI at `/config`. There is no config file to edit at runtime.

## Initial seeding

On first startup, the server reads `config.yaml` (if it exists) and seeds any keys it finds into the `AppConfig` database table. Subsequent restarts skip keys that already exist in the DB — edit them via the web UI instead.

```bash
cp config.example.yaml config.yaml
# Edit config.yaml, then start the server — values are seeded once
```

`config.yaml` is gitignored. After the initial seed it is no longer read.

## Config keys

| Key | Default | Description |
|-----|---------|-------------|
| `gmail_label` | `INBOX` | Gmail label to fetch messages from |
| `max_messages` | `100` | Max messages per pipeline run |
| `hubspot_access_token` | `""` | HubSpot Private App token. Empty = skip HubSpot sync |
| `auto_send` | `false` | Send follow-up emails automatically during pipeline runs |
| `google_doc_id` | `""` | Google Doc ID for email templates (overrides built-in templates when set) |
| `spreadsheet_id` | `""` | Google Sheets ID for legacy row export (optional) |
| `content_limit` | `5000` | Max characters stored in the email body column |

## Decision tree

The decision tree is seeded from `decision_tree.yaml` on first startup, then stored in the DB. Edit it live via the web UI at `/config` → Decision Tree section. Changes take effect on the next pipeline run.

`decision_tree.yaml` is the seed source only — the DB is the live source of truth after first run.

See the in-app [Decision Tree Guide](/guide/decision-tree) for syntax reference.

## Email templates

Templates are seeded with empty bodies from the leaf node names in `decision_tree.yaml`. Edit them via the web UI at `/config` → Templates section.

Template variables:

| Variable | Value |
|----------|-------|
| `{name}` | Contact's extracted name |
| `{address}` | Contact's extracted address |
| `{city}` | Nearest charger city |
| `{state}` | Contact's driver state |

Unknown variables are left as-is (no error).

See the in-app [Email Template Guide](/guide/templates) for full authoring instructions.

## Geocoding cache

Addresses are geocoded using [Nominatim](https://nominatim.openstreetmap.org/) (OpenStreetMap), rate-limited to 1 req/sec. Results are cached in the `GeoCache` DB table — each address is only looked up once across all pipeline runs.

If `geocache.json` exists in the repo root on first startup, it is imported into the DB automatically. Format:

```json
{
  "123 Main St, Brooklyn, NY 11205": [40.6892, -73.9442]
}
```

## Google credentials

`credentials.json` (OAuth 2.0 Desktop client secrets from Google Cloud Console) and `token.json` (saved auth tokens) are gitignored. Place them in the repo root.

Required OAuth scopes:

| Scope | Purpose |
|-------|---------|
| `gmail.modify` | Read + label Gmail messages |
| `gmail.send` | Send reply emails |
| `spreadsheets` | Read/write Google Sheets (if using legacy export) |
| `drive.readonly` | Export Google Docs for email templates |

## Chargers CSV

Charger locations are seeded from `src/itselectric/data/chargers.csv` into the `Charger` DB table on startup (idempotent). The bundled CSV has 26 entries across the US and Canada.

CSV columns: `STREET`, `CITY`, `STATE`, `ZIPCODE`, `CHARGERID`, `NUM_OF_CHARGERS`, `LAT`, `LONG`, `LAT_OVERRIDE`, `LONG_OVERRIDE`. Use `LAT_OVERRIDE`/`LONG_OVERRIDE` to correct coordinates without changing source data.

The charger list is read-only at runtime — modify the CSV and restart to update.
