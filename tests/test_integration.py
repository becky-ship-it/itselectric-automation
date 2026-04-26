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

import pytest  # type: ignore
import yaml  # type: ignore

from itselectric.decision_tree import evaluate
from itselectric.extract import extract_parsed
from itselectric.fixture import load_fixture_messages
from itselectric.geo import (
    extract_state_from_address,
    find_nearest_charger,
    geocode_address,
    load_chargers,
)
from itselectric.gmail import body_to_plain, format_sent_date, get_body_from_payload

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "emails"
TREE_PATH = Path(__file__).parent.parent / "decision_tree.example.yaml"

# Pre-populated cache entries for all fixture addresses.
# Coordinates are chosen to produce the expected routing outcome (see comments).
GEOCACHE = {
    # 01 / 02 — Brooklyn addresses at/near charger coords → general_car_info (distance <= 0.5)
    "19 Morris Ave, Brooklyn, NY 11205": [40.698863, -73.975029],
    "15 Washington St., Brooklyn, NY 11205": [40.700122, -73.967773],
    # 04 — Boston MA, ~1.2 mi from nearest Boston charger → tell_me_more_massachusetts
    "1 Cambridge St, Boston, MA 02114": [42.358, -71.064],
    # 05 — Washington DC, ~1.5 mi from DC charger → tell_me_more_dc
    "1100 16th St NW, Washington, DC 20036": [38.903, -77.036],
    # 06 — Los Angeles CA, ~1.3 mi from LA charger, distance <= 10 → tell_me_more_general
    "123 N Vermont Ave, Los Angeles, CA 90004": [34.078, -118.291],
    # 07 — Brooklyn NY, ~0.75 mi from Brooklyn charger, distance <= 5 → tell_me_more_brooklyn
    "1 Atlantic Ave, Brooklyn, NY 11201": [40.693, -73.993],
    # 08 — Detroit MI, ~1.0 mi from Detroit charger, distance <= 10 → tell_me_more_general
    "1 Woodward Ave, Detroit, MI 48226": [42.330, -83.044],
    # 09 — Chicago IL, ~240 mi from nearest charger → waitlist (distance > 100)
    "100 N Michigan Ave, Chicago, IL 60601": [41.882, -87.624],
    # 10 — Hoboken NJ, ~3.5 mi from Brooklyn charger, NJ not in priority states → waitlist
    "100 Washington St, Hoboken, NJ 07030": [40.745, -74.028],
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
        assert len(messages) == 11

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

        assert len(parsed_rows) == 9  # all fixtures except 03_unparsed and 11_bad_email
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
        assert unparsed_count == 2  # 03_unparsed_contact and 11_bad_email

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

        assert len(rows) == 11
        # Parsed rows have real names
        parsed_rows = [r for r in rows if r[1]]
        assert len(parsed_rows) == 9
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


class TestDecisionTreeRouting:
    """Full pipeline: fixture email → extract → geo → decision tree → expected template."""

    # Maps fixture address → expected template name (None = unparsed, skip routing).
    _EXPECTED: dict[str, str | None] = {
        "19 Morris Ave, Brooklyn, NY 11205": "general_car_info",
        "15 Washington St., Brooklyn, NY 11205": "general_car_info",
        "1 Cambridge St, Boston, MA 02114": "tell_me_more_massachusetts",
        "1100 16th St NW, Washington, DC 20036": "tell_me_more_dc",
        "123 N Vermont Ave, Los Angeles, CA 90004": "tell_me_more_general",
        "1 Atlantic Ave, Brooklyn, NY 11201": "tell_me_more_brooklyn",
        "1 Woodward Ave, Detroit, MI 48226": "tell_me_more_general",
        "100 N Michigan Ave, Chicago, IL 60601": "waitlist",
        "100 Washington St, Hoboken, NJ 07030": "waitlist",
    }

    @pytest.fixture(autouse=True)
    def setup(self, geocache_file, chargers):
        self.geocache_file = geocache_file
        self.chargers = chargers
        with open(TREE_PATH) as f:
            self.tree = yaml.safe_load(f)

    def test_all_fixtures_route_to_expected_template(self):
        messages = load_fixture_messages(FIXTURES_DIR)
        results = {}

        for msg in messages:
            mime, body_text = get_body_from_payload(msg.get("payload", {}))
            plain = body_to_plain(mime, body_text)
            parsed = extract_parsed(plain)
            if not parsed:
                continue

            coords = geocode_address(parsed["address"], cache_path=self.geocache_file)
            if not coords:
                continue

            result = find_nearest_charger(*coords, self.chargers)
            if not result:
                continue

            charger_dict, dist = result
            ctx = {
                "driver_state": extract_state_from_address(parsed["address"]),
                "charger_state": charger_dict["state"],
                "charger_city": charger_dict["city"],
                "distance_miles": dist,
            }
            results[parsed["address"]] = evaluate(self.tree, ctx)

        for address, expected in self._EXPECTED.items():
            assert results[address] == expected, (
                f"{address!r}: expected {expected!r}, got {results.get(address)!r}"
            )
