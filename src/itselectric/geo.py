"""Geocoding and charger proximity utilities."""

import csv
import json
import re
from functools import cache
from pathlib import Path

from geopy.distance import geodesic
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

DEFAULT_CHARGERS_CSV = Path(__file__).parent / "data" / "chargers.csv"

# Matches apartment/unit designators that confuse geocoders.
# Examples: "APT #5", "Apt. 3B", "Apartment 12", "Suite 100", "Unit 4B"
_UNIT_RE = re.compile(r",?\s*\b(?:apt|apartment|suite|ste|unit|unt)\.?\s*#?\s*\w+", re.IGNORECASE)

_nominatim = Nominatim(user_agent="itselectric-automation/1.0")
_geocode_fn = RateLimiter(_nominatim.geocode, min_delay_seconds=1)


@cache
def load_chargers(csv_path=DEFAULT_CHARGERS_CSV) -> list[dict]:
    """
    Load charger locations from a CSV file.

    Expects columns: STREET, CITY, STATE, LAT, LONG, LAT_OVERRIDE, LONG_OVERRIDE.
    Uses LAT_OVERRIDE/LONG_OVERRIDE when non-empty, otherwise LAT/LONG.
    Name is constructed as "STREET, CITY, STATE".

    Args:
        csv_path: Path to the chargers CSV file. Defaults to the bundled data file.

    Returns:
        List of dicts with keys: name (str), lat (float), lon (float).

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Chargers CSV not found: {path}")

    chargers = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            lat_raw = row.get("LAT_OVERRIDE", "").strip()
            lon_raw = row.get("LONG_OVERRIDE", "").strip()
            if not lat_raw or not lon_raw:
                lat_raw = row["LAT"].strip()
                lon_raw = row["LONG"].strip()
            chargers.append(
                {
                    "name": (
                        f"{row['STREET'].strip()}, {row['CITY'].strip()}, {row['STATE'].strip()}"
                    ),
                    "lat": float(lat_raw),
                    "lon": float(lon_raw),
                }
            )
    return chargers


def find_nearest_charger(lat: float, lon: float, chargers: list[dict]) -> tuple[str, float] | None:
    """
    Find the closest charger to (lat, lon).

    Args:
        lat: Latitude of the query point.
        lon: Longitude of the query point.
        chargers: List of charger dicts, each with keys lat, lon, and name.

    Returns:
        A (charger_name, distance_miles) tuple with distance rounded to 2 decimal
        places, or None if the chargers list is empty.
    """
    if not chargers:
        return None
    point = (lat, lon)
    nearest = min(chargers, key=lambda c: geodesic(point, (c["lat"], c["lon"])).miles)
    distance = round(geodesic(point, (nearest["lat"], nearest["lon"])).miles, 2)
    return nearest["name"], distance


def _strip_unit(address: str) -> str:
    """Remove apartment/unit designators from an address before geocoding."""
    return _UNIT_RE.sub("", address).strip().strip(",").strip()


def geocode_address(
    address: str | None,
    cache_path: str | Path | None = None,
) -> tuple[float, float] | None:
    """
    Geocode a plain-text address string to (latitude, longitude).

    Results are cached to a JSON file at cache_path (if provided) to avoid
    redundant API calls, as recommended by the Nominatim usage policy.
    Rate-limited to 1 req/sec per Nominatim ToS.

    Args:
        address: Human-readable address string to geocode.
        cache_path: Optional path to a JSON cache file. Cache is read before
            making an API call; new results are written back after a successful
            geocode. Caching is best-effort — OSError on write is silently ignored.

    Returns:
        (latitude, longitude) float tuple, or None if address is empty/blank or
        the geocoder cannot resolve it.
    """
    if not address or not address.strip():
        return None

    # Strip apt/unit numbers — they confuse geocoders and are not needed for
    # locating the building. The normalized form is used as the cache key so
    # different unit numbers at the same address share one cache entry.
    address = _strip_unit(address)
    if not address:
        return None

    # ── Read cache ────────────────────────────────────────────────────────────
    cache: dict = {}
    if cache_path is not None:
        cache_path = Path(cache_path)
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text())
            except (json.JSONDecodeError, OSError):
                cache = {}
        if address in cache:
            lat, lon = cache[address]
            return float(lat), float(lon)

    # ── Geocode via Nominatim ─────────────────────────────────────────────────
    location = _geocode_fn(address)
    if location is None:
        return None

    lat, lon = location.latitude, location.longitude

    # ── Write cache ───────────────────────────────────────────────────────────
    if cache_path is not None:
        cache[address] = [lat, lon]
        try:
            cache_path.write_text(json.dumps(cache, indent=2))
        except OSError:
            pass  # non-fatal: caching is best-effort

    return lat, lon
