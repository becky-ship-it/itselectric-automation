"""Tests for geo module: loading chargers and proximity logic."""

import json
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from itselectric.geo import (
    _strip_unit,
    find_nearest_charger,
    geocode_address,
    load_chargers,
)

# ── _strip_unit ───────────────────────────────────────────────────────────────


def test_strip_unit_apt_hash():
    assert _strip_unit("123 Main St, APT #5, Brooklyn, NY 11205") == "123 Main St, Brooklyn, NY 11205"


def test_strip_unit_apt_no_hash():
    assert _strip_unit("123 Main St, APT 5B, Brooklyn, NY 11205") == "123 Main St, Brooklyn, NY 11205"


def test_strip_unit_apartment_word():
    assert _strip_unit("123 Main St, Apartment 3B, Boston, MA") == "123 Main St, Boston, MA"


def test_strip_unit_suite():
    assert _strip_unit("456 Park Ave, Suite 100, New York, NY") == "456 Park Ave, New York, NY"


def test_strip_unit_no_unit_unchanged():
    assert _strip_unit("19 Morris Ave, Brooklyn, NY 11205") == "19 Morris Ave, Brooklyn, NY 11205"


# Real-world multi-word unit values seen in the wild
def test_strip_unit_apt_hash_word_number():
    assert _strip_unit("123 Main St, APT #Stage 11, Brooklyn, NY 11205") == "123 Main St, Brooklyn, NY 11205"


def test_strip_unit_apt_hash_no_space():
    assert _strip_unit("123 Main St, APT#Unit 430, Brooklyn, NY 11205") == "123 Main St, Brooklyn, NY 11205"


def test_strip_unit_apt_hash_space_word_number():
    assert _strip_unit("123 Main St, APT # UNIT 6005, Brooklyn, NY 11205") == "123 Main St, Brooklyn, NY 11205"


def test_strip_unit_apt_hash_apt_number():
    assert _strip_unit("123 Main St, APT #Apt 602, Brooklyn, NY 11205") == "123 Main St, Brooklyn, NY 11205"


def test_geocode_address_strips_apt_before_api_call(tmp_path):
    """APT number is removed before the geocoder is called."""
    mock_location = MagicMock()
    mock_location.latitude = 40.70
    mock_location.longitude = -73.97

    cache_file = tmp_path / "geocache.json"
    with patch("itselectric.geo._geocode_fn") as mock_fn:
        mock_fn.return_value = mock_location
        geocode_address("19 Morris Ave, APT #4A, Brooklyn, NY 11205", cache_path=cache_file)
        # The geocoder must be called with the stripped address
        mock_fn.assert_called_once_with("19 Morris Ave, Brooklyn, NY 11205")


def test_geocode_address_apt_variants_share_cache_entry(tmp_path):
    """Different unit numbers at the same address share one geocache entry."""
    mock_location = MagicMock()
    mock_location.latitude = 40.70
    mock_location.longitude = -73.97

    cache_file = tmp_path / "geocache.json"
    with patch("itselectric.geo._geocode_fn") as mock_fn:
        mock_fn.return_value = mock_location
        geocode_address("19 Morris Ave, APT #1A, Brooklyn, NY 11205", cache_path=cache_file)
        geocode_address("19 Morris Ave, APT #2B, Brooklyn, NY 11205", cache_path=cache_file)
        # Second call should hit cache — geocoder called only once
        assert mock_fn.call_count == 1


# ── load_chargers ─────────────────────────────────────────────────────────────


def test_load_chargers_uses_lat_long(tmp_path):
    csv_file = tmp_path / "chargers.csv"
    csv_file.write_text(
        textwrap.dedent("""\
        STREET,CITY,STATE,ZIPCODE,CHARGERID,NUM_OF_CHARGERS,LAT,LONG,LAT_OVERRIDE,LONG_OVERRIDE
        11 Spring St,Newburgh,NY,12550,NBG01,1,41.496385,-74.01174,,
    """)
    )
    chargers = load_chargers(csv_file)
    assert len(chargers) == 1
    assert chargers[0]["name"] == "11 Spring St, Newburgh, NY"
    assert chargers[0]["lat"] == pytest.approx(41.496385)
    assert chargers[0]["lon"] == pytest.approx(-74.01174)


def test_load_chargers_prefers_override(tmp_path):
    csv_file = tmp_path / "chargers.csv"
    csv_file.write_text(
        textwrap.dedent("""\
        STREET,CITY,STATE,ZIPCODE,CHARGERID,NUM_OF_CHARGERS,LAT,LONG,LAT_OVERRIDE,LONG_OVERRIDE
        15 Washington St.,Brooklyn,NY,11205,S01,1,40.703503,-73.989561,40.700122,-73.967773
    """)
    )
    chargers = load_chargers(csv_file)
    assert chargers[0]["lat"] == pytest.approx(40.700122)
    assert chargers[0]["lon"] == pytest.approx(-73.967773)


def test_load_chargers_missing_file():
    with pytest.raises(FileNotFoundError):
        load_chargers("/nonexistent/path/chargers.csv")


def test_load_chargers_default_path_exists():
    chargers = load_chargers()
    assert len(chargers) > 0
    assert "lat" in chargers[0]
    assert "lon" in chargers[0]
    assert "name" in chargers[0]


# ── load_chargers city/state fields ──────────────────────────────────────────


def test_load_chargers_includes_city_and_state():
    """load_chargers dicts include city and state fields."""
    chargers = load_chargers()
    assert chargers
    first = chargers[0]
    assert "city" in first
    assert "state" in first
    assert isinstance(first["city"], str)
    assert isinstance(first["state"], str)


def test_load_chargers_city_state_values(tmp_path):
    """city and state are populated from CSV columns."""
    csv_file = tmp_path / "chargers.csv"
    csv_file.write_text(
        "STREET,CITY,STATE,ZIPCODE,CHARGERID,NUM_OF_CHARGERS,LAT,LONG,LAT_OVERRIDE,LONG_OVERRIDE\n"
        "11 Spring St,Newburgh,NY,12550,NBG01,1,41.496385,-74.01174,,\n"
    )
    chargers = load_chargers(csv_file)
    assert chargers[0]["city"] == "Newburgh"
    assert chargers[0]["state"] == "NY"


# ── find_nearest_charger ──────────────────────────────────────────────────────

CHARGERS = [
    {"name": "Hub A", "city": "Brooklyn", "state": "NY", "lat": 40.7002, "lon": -73.9722},
    {"name": "Hub B", "city": "Manhattan", "state": "NY", "lat": 40.7282, "lon": -73.9542},
]


def test_find_nearest_charger_returns_charger_dict():
    """find_nearest_charger returns (charger_dict, distance), not (name_str, distance)."""
    charger_dict, dist = find_nearest_charger(40.700, -73.972, CHARGERS)
    assert isinstance(charger_dict, dict)
    assert charger_dict["name"] == "Hub A"
    assert charger_dict["city"] == "Brooklyn"
    assert charger_dict["state"] == "NY"
    assert dist < 0.2


def test_find_nearest_charger_returns_closest():
    charger_dict, dist = find_nearest_charger(40.700, -73.972, CHARGERS)
    assert charger_dict["name"] == "Hub A"
    assert dist < 0.2


def test_find_nearest_charger_empty_returns_none():
    assert find_nearest_charger(40.700, -73.972, []) is None


def test_find_nearest_charger_returns_float_distance():
    charger_dict, dist = find_nearest_charger(40.7135, -73.9754, CHARGERS)
    assert isinstance(dist, float)
    assert dist > 0


# ── geocode_address ───────────────────────────────────────────────────────────


def test_geocode_address_success(tmp_path):
    mock_location = MagicMock()
    mock_location.latitude = 40.7128
    mock_location.longitude = -74.0060

    cache_file = tmp_path / "geocache.json"
    with patch("itselectric.geo._geocode_fn") as mock_fn:
        mock_fn.return_value = mock_location
        result = geocode_address("New York, NY", cache_path=cache_file)

    assert result == (pytest.approx(40.7128), pytest.approx(-74.0060))


def test_geocode_address_writes_cache(tmp_path):
    mock_location = MagicMock()
    mock_location.latitude = 40.7128
    mock_location.longitude = -74.0060

    cache_file = tmp_path / "geocache.json"
    with patch("itselectric.geo._geocode_fn") as mock_fn:
        mock_fn.return_value = mock_location
        geocode_address("New York, NY", cache_path=cache_file)

    cache = json.loads(cache_file.read_text())
    assert "New York, NY" in cache
    assert cache["New York, NY"] == pytest.approx([40.7128, -74.0060])


def test_geocode_address_reads_cache_no_api_call(tmp_path):
    cache_file = tmp_path / "geocache.json"
    cache_file.write_text(json.dumps({"123 Main St": [42.0, -71.0]}))

    with patch("itselectric.geo._geocode_fn") as mock_fn:
        result = geocode_address("123 Main St", cache_path=cache_file)
        mock_fn.assert_not_called()

    assert result == (pytest.approx(42.0), pytest.approx(-71.0))


def test_geocode_address_not_found(tmp_path):
    cache_file = tmp_path / "geocache.json"
    with patch("itselectric.geo._geocode_fn") as mock_fn:
        mock_fn.return_value = None
        result = geocode_address("zzz not a real address", cache_path=cache_file)
    assert result is None


def test_geocode_address_empty():
    assert geocode_address("") is None
    assert geocode_address(None) is None
