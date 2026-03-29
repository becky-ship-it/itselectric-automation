# Testing

## Running tests

```bash
uv run pytest          # all tests
uv run pytest -v       # verbose output
uv run pytest tests/test_geo.py -v                                          # single file
uv run pytest tests/test_integration.py::TestFullPipeline::test_full_row_building -v  # single test
```

No `credentials.json` or `token.json` is needed to run the test suite.

## Test suite

| File | What it covers |
|------|---------------|
| `test_extract.py` | Regex extraction — parsed matches, no-match, empty, None input |
| `test_fixture.py` | `load_fixture_messages` — body roundtrip, date parsing, sort order, non-txt filtering |
| `test_geo.py` | `load_chargers`, `geocode_address` (cache read/write/hit), `find_nearest_charger` |
| `test_gmail.py` | `get_body_from_payload` (single-part, multipart, nested), `body_to_plain`, `format_sent_date` |
| `test_gui_pipeline.py` | `_run_pipeline` completion guarantees, stdout restoration, success/failure routing |
| `test_integration.py` | Full end-to-end: fixture files → extract → geocache → nearest charger → row tuples |
| `test_sheets.py` | `row_hash` deduplication — parsed vs unparsed hash strategies |
| `test_hubspot.py` | `upsert_contact` — success, endpoint shape, name splitting, error handling |

## Integration tests

`tests/test_integration.py` exercises the full pipeline with no network calls or credentials:

1. Emails loaded from `tests/fixtures/emails/*.txt`
2. Geocoding reads from a pre-populated in-memory cache (no Nominatim calls)
3. Real bundled `chargers.csv` used for proximity lookup

## Fixture emails

Each fixture email is a plain `.txt` file in `tests/fixtures/emails/`. Files are loaded in sorted filename order. The body must match the extraction regex:

```
it's electric <Name> The user has an address of <Address> and has an email of
<email_1>
Email address submitted in form
<email_2>
```

Any file that doesn't match the pattern is treated as an unparsed email (recorded with empty parsed columns).

To test locally without credentials:

```bash
uv run itselectric --fixture-dir tests/fixtures/emails
```

## Adding a new extraction pattern

The regex lives in `src/itselectric/extract.py`. To support a different email format:

1. Edit `EXTRACT_PATTERN` in `extract.py`.
2. Add a fixture file in `tests/fixtures/emails/` with sample content.
3. Add unit tests in `tests/test_extract.py`.
4. Run `uv run pytest tests/test_extract.py tests/test_integration.py -v`.

Note: `extract_parsed` prepends `"[plain]: "` before matching, so fixture files should **not** include that prefix.

## Linting

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

Rules: `E`, `F`, `I` — line length 100.
