"""Geocoding and charger proximity utilities."""

import csv
import json
import re
from functools import cache
from pathlib import Path

from geopy.distance import geodesic  # type: ignore
from geopy.exc import GeocoderServiceError  # type: ignore
from geopy.extra.rate_limiter import RateLimiter  # type: ignore
from geopy.geocoders import Geocodio, Nominatim  # type: ignore

DEFAULT_CHARGERS_CSV = Path(__file__).parent / "data" / "chargers.csv"

# Matches apartment/unit designators that confuse geocoders.
# The unit VALUE is bounded to the designator token itself (a #-prefixed value
# ending in a number, or a bare number like "5"/"3B"/"210") rather than
# "everything up to the next comma". This matters for comma-less human input
# such as "88 park ave suite 12 brooklyn ny": a comma-anchored match would eat
# "12 brooklyn ny" and leave only the street, sending the geocoder to the wrong
# city. Handles multi-word #-values seen in the wild: "APT #Stage 11",
# "APT#Unit 430", "APT # UNIT 6005".
#
# The designator list mirrors the USPS secondary-unit designators (Publication
# 28, Appendix C2) so that a unit in its own comma segment ("..., Floor 3,
# Brooklyn") is stripped instead of leaking into the city field on the regex
# fallback path. Every alternative still requires a trailing number, so real
# city names ("North Haven", "Novato") are not eaten. A bare "#12" segment with
# no keyword is also handled.
_UNIT_RE = re.compile(
    r",?\s*\b(?:apt|apartment|suite|ste|unit|unt|bldg|building|fl|floor|rm|room|"
    r"dept|department|lot|space|spc|trlr|trailer|hangar|hngr|slip|pier|stop|"
    r"no|number)\.?\s*(?:#\s*[^,]*?\d+[A-Za-z]?|\d+[A-Za-z]?)"
    r"|,?\s*#\s*\w*\d+[A-Za-z]?",
    re.IGNORECASE,
)

# Matches a 2-letter US state abbreviation preceded by a comma, optionally
# followed by a ZIP code, at the end of the address string.
_STATE_ABBREV_RE = re.compile(r",\s*([A-Z]{2})\s*(?:\d{5}(?:-\d{4})?)?\s*$", re.IGNORECASE)

# Matches a full state name (1-3 words) preceded by a comma, optionally
# followed by a ZIP code, at the end of the address string.
_STATE_FULLNAME_RE = re.compile(
    r",\s*([A-Za-z]+(?:\s+[A-Za-z]+){0,2}?)\s*(?:\d{5}(?:-\d{4})?)?\s*$"
)

# Maps lowercased full state names to 2-letter USPS abbreviations.
_STATE_NAME_TO_ABBREV: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}


def extract_state_from_address(address: str | None) -> str | None:
    """
    Extract the US state abbreviation from a free-text address string.

    Tries two strategies in order:
    1. Look for a 2-letter abbreviation (e.g. "TX", "CA") at the end of the string.
    2. Look for a full state name (e.g. "Texas", "North Carolina") and map it to
       its abbreviation via a lookup table.

    Returns the 2-letter abbreviation in uppercase, or None only if the state
    is genuinely absent or misspelled.
    """
    if not address or not address.strip():
        return None
    address = address.strip()

    # Strategy 1: 2-letter abbreviation
    m = _STATE_ABBREV_RE.search(address)
    if m:
        return m.group(1).upper()

    # Strategy 2: full state name lookup
    m = _STATE_FULLNAME_RE.search(address)
    if m:
        candidate = m.group(1).strip().lower()
        abbrev = _STATE_NAME_TO_ABBREV.get(candidate)
        if abbrev:
            return abbrev

    return None


def parse_address_components(address: str) -> dict[str, str]:
    """
    Split a US address string into street, city, state, and zip.
    Expected format: '123 Main St, City, ST 12345' or '123 Main St, City, ST'.
    Falls back gracefully — missing parts return empty strings.
    """
    address = (address or "").strip()
    # street, city, ST 12345
    m = re.match(r"^(.+?),\s*(.+?),\s*([A-Za-z]{2})\s+(\d{5}(?:-\d{4})?)$", address)
    if m:
        return {
            "street": m.group(1), "city": m.group(2),
            "state": m.group(3).upper(), "zip": m.group(4),
        }
    # street, city, ST  (no zip)
    m = re.match(r"^(.+?),\s*(.+?),\s*([A-Za-z]{2})$", address)
    if m:
        return {"street": m.group(1), "city": m.group(2), "state": m.group(3).upper(), "zip": ""}
    # street, city  (no state/zip)
    m = re.match(r"^(.+?),\s*(.+)$", address)
    if m:
        return {"street": m.group(1), "city": m.group(2), "state": "", "zip": ""}
    return {"street": address, "city": "", "state": "", "zip": ""}


def resolve_address_components(
    address: str, geocodio_api_key: str | None = None
) -> dict[str, str]:
    """
    Resolve an address into street/city/state/zip components, preferring
    Geocodio's structured output over regex string-splitting.

    Geocodio returns parsed ``address_components`` (city, state, zip separate
    from the street line), so apartment/unit numbers do not leak into the city
    the way they do with positional comma-splitting. When no key is set, or
    Geocodio errors or returns no components, this falls back to
    ``parse_address_components`` on the unit-stripped address.

    Address line 1 (house number + street) and the secondary unit (e.g. "Apt 4")
    are returned separately as ``street`` and ``unit`` so they map to distinct
    CRM properties. Neither ever contains the city, state, or zip.

    Args:
        address: Human-readable address string.
        geocodio_api_key: Optional Geocodio API key. When set, Geocodio is tried
            first for city/state/zip.

    Returns:
        Dict with keys ``street``, ``unit``, ``city``, ``state``, ``zip``.
        Missing parts are empty strings.
    """
    address = (address or "").strip()
    fallback = parse_address_components(_strip_unit(address))
    fallback["unit"] = ""
    if not geocodio_api_key or not address:
        return fallback

    try:
        loc = _geocodio(geocodio_api_key).geocode(address)
    except GeocoderServiceError:
        return fallback
    comps = (loc.raw.get("address_components") if loc is not None else None) or {}
    if not comps.get("city"):
        return fallback

    line1 = " ".join(
        p for p in (comps.get("number", ""), comps.get("formatted_street", "")) if p
    ).strip()
    unit = " ".join(
        p for p in (comps.get("secondaryunit", ""), comps.get("secondarynumber", "")) if p
    ).strip()
    return {
        "street": line1 or address,
        "unit": unit,
        "city": comps.get("city", ""),
        "state": comps.get("state", ""),
        "zip": comps.get("zip", ""),
    }


_nominatim = Nominatim(user_agent="itselectric-automation/1.0", timeout=10)
_geocode_fn = RateLimiter(_nominatim.geocode, min_delay_seconds=1)


@cache
def _geocodio(api_key: str) -> Geocodio:
    """Build (and memoize) a Geocodio geocoder for the given API key."""
    return Geocodio(api_key=api_key, timeout=10)


def _geocode_once(address: str, geocodio_api_key: str | None) -> tuple[float, float] | None:
    """
    Resolve an address to (lat, lon), trying Geocodio first when a key is set,
    then falling back to Nominatim.

    Geocodio resolves messy/apartment US addresses more reliably than Nominatim
    (benchmarked: 45/45 vs 41/45 on noisy human input), so it is preferred when
    configured. Nominatim is the free fallback used when Geocodio is unset or
    errors. A provider that raises or returns nothing is treated as a miss and
    the next provider is tried.
    """
    if geocodio_api_key:
        try:
            loc = _geocodio(geocodio_api_key).geocode(address)
            if loc is not None:
                return loc.latitude, loc.longitude
        except GeocoderServiceError:
            pass  # fall through to Nominatim

    loc = _geocode_fn(address)
    if loc is not None:
        return loc.latitude, loc.longitude
    return None


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
                    "city": row["CITY"].strip().title(),
                    # Big assumption: state is always a 2-letter abbreviation in the CSV.
                    # If not, we could apply the same extraction logic as in 
                    # extract_state_from_address(), but that would be more complex and error-prone,
                    # so we just enforce the format in the data.
                    "state": row["STATE"].strip().upper(),
                    "lat": float(lat_raw),
                    "lon": float(lon_raw),
                }
            )
    return chargers


def find_nearest_charger(lat: float, lon: float, chargers: list[dict]) -> tuple[dict, float] | None:
    """
    Find the closest charger to (lat, lon).

    Args:
        lat: Latitude of the query point.
        lon: Longitude of the query point.
        chargers: List of charger dicts, each with keys lat, lon, name, city, state.

    Returns:
        A (charger_dict, distance_miles) tuple with distance rounded to 2 decimal
        places, or None if the chargers list is empty.
    """
    if not chargers:
        return None
    point = (lat, lon)
    nearest = min(chargers, key=lambda c: geodesic(point, (c["lat"], c["lon"])).miles)
    distance = round(geodesic(point, (nearest["lat"], nearest["lon"])).miles, 2)
    return nearest, distance


def _strip_unit(address: str) -> str:
    """Remove apartment/unit designators from an address before geocoding."""
    return _UNIT_RE.sub("", address).strip().strip(",").strip()


def geocode_address(
    address: str | None,
    cache_path: str | Path | None = None,
    geocodio_api_key: str | None = None,
) -> tuple[float, float] | None:
    """
    Geocode a plain-text address string to (latitude, longitude).

    Uses Geocodio when geocodio_api_key is set, falling back to Nominatim
    otherwise (or when Geocodio errors/misses). Results are cached to a JSON
    file at cache_path (if provided) to avoid redundant API calls, as
    recommended by the Nominatim usage policy. Nominatim calls are rate-limited
    to 1 req/sec per its ToS.

    Args:
        address: Human-readable address string to geocode.
        cache_path: Optional path to a JSON cache file. Cache is read before
            making an API call; new results are written back after a successful
            geocode. Caching is best-effort — OSError on write is silently ignored.
        geocodio_api_key: Optional Geocodio API key. When set, Geocodio is tried
            first; Nominatim is used as fallback.

    Returns:
        (latitude, longitude) float tuple, or None if address is empty/blank or
        no geocoder can resolve it.
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

    # ── Geocode (Geocodio if configured, else Nominatim) ──────────────────────
    coords = _geocode_once(address, geocodio_api_key)
    if coords is None:
        return None

    lat, lon = coords

    # ── Write cache ───────────────────────────────────────────────────────────
    if cache_path is not None:
        cache[address] = [lat, lon]
        try:
            cache_path.write_text(json.dumps(cache, indent=2))
        except OSError:
            pass  # non-fatal: caching is best-effort

    return lat, lon
