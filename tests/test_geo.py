"""Tests for geo module: loading chargers and proximity logic."""

import json
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from itselectric.geo import (
    DEFAULT_CHARGERS_CSV,
    find_nearest_charger,
    geocode_address,
    load_chargers,
)

# ── load_chargers ─────────────────────────────────────────────────────────────

def test_load_chargers_uses_lat_long(tmp_path):
    csv_file = tmp_path / "chargers.csv"
    csv_file.write_text(textwrap.dedent("""\
        STREET,CITY,STATE,ZIPCODE,CHARGERID,NUM_OF_CHARGERS,LAT,LONG,LAT_OVERRIDE,LONG_OVERRIDE
        11 Spring St,Newburgh,NY,12550,NBG01,1,41.496385,-74.01174,,
    """))
    chargers = load_chargers(csv_file)
    assert len(chargers) == 1
    assert chargers[0]["name"] == "11 Spring St, Newburgh, NY"
    assert chargers[0]["lat"] == pytest.approx(41.496385)
    assert chargers[0]["lon"] == pytest.approx(-74.01174)


def test_load_chargers_prefers_override(tmp_path):
    csv_file = tmp_path / "chargers.csv"
    csv_file.write_text(textwrap.dedent("""\
        STREET,CITY,STATE,ZIPCODE,CHARGERID,NUM_OF_CHARGERS,LAT,LONG,LAT_OVERRIDE,LONG_OVERRIDE
        15 Washington St.,Brooklyn,NY,11205,S01,1,40.703503,-73.989561,40.700122,-73.967773
    """))
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


# ── find_nearest_charger ──────────────────────────────────────────────────────

CHARGERS = [
    {"name": "Hub A", "lat": 40.7002, "lon": -73.9722},
    {"name": "Hub B", "lat": 40.7282, "lon": -73.9542},
]


def test_find_nearest_charger_returns_closest():
    name, dist = find_nearest_charger(40.700, -73.972, CHARGERS)
    assert name == "Hub A"
    assert dist < 0.2


def test_find_nearest_charger_empty_returns_none():
    assert find_nearest_charger(40.700, -73.972, []) is None


def test_find_nearest_charger_returns_float_distance():
    name, dist = find_nearest_charger(40.7135, -73.9754, CHARGERS)
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
