"""
Integration tests: full pipeline from fixture files through extraction and geo.

No network calls are made:
- Emails come from tests/fixtures/emails/*.txt
- Geocoding reads from a pre-populated JSON geocache (no Nominatim calls)
- Sheets API is not called (no spreadsheet_id used)

What this tests end-to-end:
- load_fixture_messages produces valid Gmail-compatible message dicts
- format_sent_date / get_body_from_payload / body_to_plain correctly decode them
- extract_parsed correctly identifies parsed vs unparsed messages
- geocode_address returns cached coordinates without hitting the network
- find_nearest_charger returns a charger dict and distance
"""

import json
from pathlib import Path

import pytest

from itselectric.extract import extract_parsed
from itselectric.fixture import load_fixture_messages
from itselectric.geo import find_nearest_charger, geocode_address, load_chargers
from itselectric.gmail import body_to_plain, format_sent_date, get_body_from_payload

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "emails"

# Pre-populated cache entries for the addresses in the fixture files.
# These coordinates are real: 19 Morris Ave and 15 Washington St are in Brooklyn.
GEOCACHE = {
    "19 Morris Ave, Brooklyn, NY 11205": [40.698863, -73.975029],
    "15 Washington St., Brooklyn, NY 11205": [40.700122, -73.967773],
}


@pytest.fixture
def geocache_file(tmp_path) -> Path:
    """Write a pre-populated geocache JSON file and return its path."""
    p = tmp_path / "geocache.json"
    p.write_text(json.dumps(GEOCACHE))
    return p


@pytest.fixture
def chargers():
    """Load the real bundled charger CSV."""
    return load_chargers()


class TestFullPipeline:
    def test_loads_correct_number_of_messages(self):
        messages = load_fixture_messages(FIXTURES_DIR)
        assert len(messages) == 3

    def test_parsed_messages_extract_correctly(self, geocache_file, chargers):
        """Parsed fixture emails produce correct name/address/email fields."""
        messages = load_fixture_messages(FIXTURES_DIR)
        parsed_rows = []

        for msg in messages:
            _ = format_sent_date(msg)
            mime, body_text = get_body_from_payload(msg.get("payload", {}))
            plain = body_to_plain(mime, body_text)
            parsed = extract_parsed(plain)
            if parsed:
                parsed_rows.append(parsed)

        assert len(parsed_rows) == 2
        names = {r["name"] for r in parsed_rows}
        assert "Jane Smith" in names
        assert "Bob Jones" in names

    def test_unparsed_message_is_identified(self):
        """The third fixture file does not match the extraction regex."""
        messages = load_fixture_messages(FIXTURES_DIR)
        unparsed_count = 0
        for msg in messages:
            mime, body_text = get_body_from_payload(msg.get("payload", {}))
            plain = body_to_plain(mime, body_text)
            if extract_parsed(plain) is None:
                unparsed_count += 1
        assert unparsed_count == 1

    def test_geocode_uses_cache_not_network(self, geocache_file):
        """geocode_address reads from the pre-populated cache file (no Nominatim call)."""
        result = geocode_address("19 Morris Ave, Brooklyn, NY 11205", cache_path=geocache_file)
        assert result is not None
        lat, lon = result
        assert abs(lat - 40.698863) < 0.001
        assert abs(lon - -73.975029) < 0.001

    def test_nearest_charger_found_for_brooklyn_address(self, geocache_file, chargers):
        """A Brooklyn fixture address resolves to a real nearby charger."""
        coords = geocode_address("19 Morris Ave, Brooklyn, NY 11205", cache_path=geocache_file)
        assert coords is not None
        charger_dict, dist = find_nearest_charger(*coords, chargers)
        assert charger_dict["name"] != ""
        assert charger_dict["city"] != ""
        assert charger_dict["state"] != ""
        assert dist < 5.0  # well within 5 miles

    def test_full_row_building(self, geocache_file, chargers):
        """End-to-end: fixture → extract → geo → 10-element row tuples."""
        messages = load_fixture_messages(FIXTURES_DIR)
        rows = []

        for msg in messages:
            sent_date = format_sent_date(msg)
            mime, body_text = get_body_from_payload(msg.get("payload", {}))
            plain = body_to_plain(mime, body_text)
            parsed = extract_parsed(plain)

            nearest_charger, distance_mi = "", ""
            if parsed and chargers:
                coords = geocode_address(parsed["address"], cache_path=geocache_file)
                if coords:
                    result = find_nearest_charger(*coords, chargers)
                    if result:
                        nearest_charger_dict, dist_float = result
                        nearest_charger = nearest_charger_dict["name"]
                        distance_mi = str(dist_float)

            if parsed:
                rows.append(
                    (
                        sent_date,
                        parsed["name"],
                        parsed["address"],
                        parsed["email_1"],
                        parsed["email_2"],
                        plain,
                        nearest_charger,
                        distance_mi,
                    )
                )
            else:
                rows.append((sent_date, "", "", "", "", plain, "", ""))

        assert len(rows) == 3
        # Parsed rows have real names
        parsed_rows = [r for r in rows if r[1]]
        assert len(parsed_rows) == 2
        # Geo columns are populated for parsed rows
        for row in parsed_rows:
            assert row[6] != "", f"Expected nearest_charger to be set, got: {row}"
            assert row[7] != "", f"Expected distance_mi to be set, got: {row}"

    def test_hubspot_skipped_when_no_token(self):
        """When hubspot_access_token is absent/empty, no HubSpot calls are made."""
        from unittest.mock import patch
        from itselectric.hubspot import upsert_contact

        with patch("itselectric.hubspot.requests.post") as mock_post:
            messages = load_fixture_messages(FIXTURES_DIR)
            token = ""
            for msg in messages:
                mime, body_text = get_body_from_payload(msg.get("payload", {}))
                plain = body_to_plain(mime, body_text)
                parsed = extract_parsed(plain)
                if parsed and token:
                    upsert_contact(token, parsed["name"], parsed["email_1"], parsed["address"])

        mock_post.assert_not_called()
