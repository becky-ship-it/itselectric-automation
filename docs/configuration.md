# Configuration

All settings live in `config.yaml` (copied from `config.example.yaml`). CLI flags override config values when both are present. `config.yaml` is gitignored — never commit it.

```bash
cp config.example.yaml config.yaml
```

## Options

| Key | Default | CLI flag | Description |
|-----|---------|----------|-------------|
| `label` | `INBOX` | `--label` | Gmail label to read (`INBOX`, `Follow Up`, etc.) |
| `max_messages` | `100` | `--max-messages` | Maximum number of messages to fetch |
| `body_length` | `200` | `--body-length` | Max characters of body to print per message (0 = no limit) |
| `spreadsheet_id` | `""` | `--spreadsheet-id` | Google Spreadsheet ID from the sheet URL. If empty, runs in preview-only mode |
| `sheet` | `Sheet1` | `--sheet` | Sheet (tab) name within the spreadsheet |
| `content_limit` | `5000` | `--content-limit` | Max characters for the Content column |
| `chargers` | *(bundled CSV)* | `--chargers` | Path to chargers CSV. Defaults to the bundled `src/itselectric/data/chargers.csv` |
| `geocache` | `geocache.json` | `--geocache` | Path to JSON file for caching geocoded addresses. Created automatically on first run |
| `fixture_dir` | `""` | `--fixture-dir` | Load emails from `.txt` files instead of Gmail. Skips all Google auth |
| `hubspot_access_token` | `""` | `--hubspot-access-token` | HubSpot access token. When set, creates/updates a CRM contact for every parsed email |

The spreadsheet ID is the long string in the sheet URL:
```
https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
```

## Geocoding cache

Addresses are geocoded using [Nominatim](https://nominatim.openstreetmap.org/) (OpenStreetMap), rate-limited to 1 request/second. Results are cached in `geocache.json` so each address is only looked up once:

```json
{
  "123 Main St, Brooklyn, NY 11205": [40.6892, -73.9442]
}
```

You can pre-populate this file with known addresses to avoid any API calls entirely.

## Chargers CSV format

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
| `LAT_OVERRIDE` | Corrected latitude (overrides `LAT` when non-empty) |
| `LONG_OVERRIDE` | Corrected longitude (overrides `LONG` when non-empty) |

To use a custom charger list, provide a CSV with the same columns and set `chargers` in `config.yaml`.
