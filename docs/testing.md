# Testing

## Running tests

```bash
uv run pytest tests/ -v          # all 207 Python tests
uv run pytest tests/test_geo.py  # single file
uv run pytest -k "test_full"     # by name pattern

cd web && npm test               # Vitest unit tests (Config, History pages)
cd web && npx playwright test    # E2E browser tests (server must be running on :8000)
```

No `credentials.json`, `token.json`, or network access required for the Python suite.

## Python test suite (207 tests)

| File | Count | What's covered |
|------|-------|----------------|
| `test_geo.py` | 39 | `geocode_address`, `load_chargers`, `find_nearest_charger`, `extract_state_from_address`, `parse_address_components` |
| `test_decision_tree.py` | 36 | All operators, nested trees, all routing paths in `decision_tree.example.yaml` |
| `test_gmail.py` | 32 | `get_body_from_payload`, `body_to_plain`, `format_sent_date`, `load_template`, `send_email` |
| `test_sheets.py` | 16 | `row_hash` dedup strategies, column structure, `append_rows` |
| `test_seed.py` | 11 | DB seeding: chargers, geocache, decision tree, templates, config |
| `test_api_templates.py` | 9 | Template list, get, save endpoints |
| `test_integration.py` | 8 | Full pipeline: fixture files → extract → geocache → charger → row tuples + routing |
| `test_fixture.py` | 7 | `load_fixture_messages`: body roundtrip, date, sort order, non-txt filter |
| `test_api_contacts.py` | 6 | Contact list, detail, send, fix endpoints |
| `test_api_config.py` | 6 | Config get/set endpoints |
| `test_api_chargers.py` | 6 | Charger list endpoint |
| `test_pipeline_service.py` | 5 | `run_pipeline` with fixture mode, HubSpot skip, auto-send gate |
| `test_hubspot.py` | 5 | `upsert_contact`: success, endpoint shape, name splitting, error handling |
| `test_email_layout.py` | 5 | `render_email` HTML structure, logo presence |
| `test_api_export.py` | 5 | CSV and JSON export endpoints |
| `test_extract.py` | 4 | Regex match, no-match, empty, None input |
| `test_api_pipeline.py` | 4 | Pipeline run endpoints |
| `test_models.py` | 3 | ORM model field defaults and relationships |

## E2E test suite (18 tests, Playwright)

Tests run headless against the live server at `http://localhost:8000`. Start it with `./run_server.sh` first.

| Group | Tests |
|-------|-------|
| Navigation | Sidebar links, direct URL routing (SPA) |
| Dashboard | Heading, status counts, pipeline buttons |
| Inbox | All/Pending/Unparsed tabs, contact list, detail panel, email preview |
| History | Table headers, search filter, CSV/JSON download links |
| Config | Templates section, Decision Tree section, Guide links, template editor, guide pages |
| Logs | Heading, Auto-scroll toggle, Clear button |

## Integration tests

`tests/test_integration.py` exercises the full pipeline with no network calls:

1. Emails loaded from `tests/fixtures/emails/*.txt` (11 files)
2. Geocoding reads from a pre-populated in-memory cache written to `tmp_path`
3. Real bundled `chargers.csv` used for proximity lookup
4. `decision_tree.example.yaml` used for routing assertions

## Fixture emails

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
| `11_bad_email.txt` | 123 Oak Stret Austn TX _(malformed)_ | unparsed |

## Adding a new extraction pattern

1. Edit `EXTRACT_PATTERN` in `src/itselectric/extract.py`
2. Add a fixture file in `tests/fixtures/emails/` with sample content
3. Add unit tests in `tests/test_extract.py`
4. Run `uv run pytest tests/test_extract.py tests/test_integration.py -v`

## Linting

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

Rules: `E`, `F`, `I` — line length 100.
