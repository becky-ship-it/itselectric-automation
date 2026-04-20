# Email Decision Tree Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow the client to define a YAML decision tree that selects which HubSpot transactional email to send each incoming cable-request driver, based on their location relative to the nearest charger.

**Architecture:** A new `decision_tree.py` module walks a YAML-configured tree of conditions (distance, state, city) and returns a HubSpot email template ID. The pipeline in `cli.py` evaluates this tree after geocoding and calls a new `send_email` helper in `hubspot.py`. Geo data needs minor surgery to expose structured `city`/`state` fields on charger dicts and return a richer result from `find_nearest_charger`.

**Tech Stack:** Python stdlib + PyYAML (already installed for config loading) + HubSpot Marketing Transactional Email API (`POST /marketing/v3/transactional/single-email/send`)

---

## Decision Tree YAML Format

The client edits a standalone YAML file (e.g. `decision_tree.yaml`) that is referenced from `config.yaml` via the `decision_tree_file` key.

Each node in the tree is **either** a branch or a leaf:

```yaml
# Branch node:
condition:
  field: distance_miles    # driver_state | charger_state | charger_city | distance_miles
  op: lt                   # lt | lte | gt | gte | eq | ne | in
  value: 0.5               # scalar, or list when op=in
yes: <node>
no: <node>

# Leaf node (send an email):
email_id: 12345            # HubSpot transactional email template ID (integer)

# Leaf node (do nothing — explicit no-op):
email_id: null
```

**Full example matching the spec:**

```yaml
# decision_tree.yaml
condition:
  field: distance_miles
  op: lt
  value: 0.5
yes:
  email_id: 11111          # Get General Car Info
no:
  condition:
    field: distance_miles
    op: lt
    value: 100
  yes:
    condition:
      field: driver_state
      op: eq
      value: CA
    yes:
      condition:
        field: charger_city
        op: in
        value:
          - Los Angeles
          - San Francisco
      yes:
        email_id: 67890    # Get California Car Info
      no:
        email_id: 22222    # Waitlist
    no:
      email_id: 11111      # Get General Car Info
  no:
    email_id: 22222        # Waitlist
```

**Context fields available at evaluation time:**

| Field | Type | Example | Source |
|---|---|---|---|
| `driver_state` | str (2-letter) | `"CA"` | Parsed from extracted address |
| `charger_state` | str (2-letter) | `"CA"` | Charger CSV `STATE` column |
| `charger_city` | str | `"Los Angeles"` | Charger CSV `CITY` column |
| `distance_miles` | float | `14.7` | `find_nearest_charger` result |

---

## Task 1: Extend charger dicts with city/state and update find_nearest_charger return type

**Why:** The decision tree needs `charger_city` and `charger_state` as structured values. `load_chargers` already reads `CITY`/`STATE` from the CSV — we just need to keep them in the dict. `find_nearest_charger` currently returns `(name_str, distance)` — changing it to `(charger_dict, distance)` lets callers access city/state without re-parsing the name string.

**Files:**
- Modify: `src/itselectric/geo.py`
- Modify: `src/itselectric/cli.py` (call site update)
- Modify: `src/itselectric/gui.py` (call site update)
- Modify: `tests/test_geo.py`

**Step 1: Write the failing tests**

```python
# In tests/test_geo.py — add to the existing test class

def test_load_chargers_includes_city_and_state():
    """load_chargers dicts include city and state fields."""
    chargers = load_chargers()
    assert chargers  # sanity check
    first = chargers[0]
    assert "city" in first
    assert "state" in first
    assert isinstance(first["city"], str)
    assert isinstance(first["state"], str)

def test_find_nearest_charger_returns_charger_dict():
    """find_nearest_charger returns (charger_dict, distance) not (name_str, distance)."""
    chargers = [
        {"name": "1 Main St, Boston, MA", "city": "Boston", "state": "MA", "lat": 42.36, "lon": -71.06},
        {"name": "2 Far St, Denver, CO", "city": "Denver", "state": "CO", "lat": 39.73, "lon": -104.99},
    ]
    result = find_nearest_charger(42.36, -71.06, chargers)
    assert result is not None
    charger_dict, distance = result
    assert isinstance(charger_dict, dict)
    assert charger_dict["city"] == "Boston"
    assert charger_dict["state"] == "MA"
    assert charger_dict["name"] == "1 Main St, Boston, MA"
    assert distance < 1.0
```

**Step 2: Run tests to confirm they fail**

```bash
source .venv/bin/activate
pytest tests/test_geo.py::test_load_chargers_includes_city_and_state tests/test_geo.py::test_find_nearest_charger_returns_charger_dict -v
```
Expected: FAIL — `city`/`state` keys missing, and `charger_dict` is still a string.

**Step 3: Implement the changes in geo.py**

In `load_chargers`, extend the dict appended for each row:
```python
chargers.append(
    {
        "name": f"{row['STREET'].strip()}, {row['CITY'].strip()}, {row['STATE'].strip()}",
        "city": row["CITY"].strip(),
        "state": row["STATE"].strip(),
        "lat": float(lat_raw),
        "lon": float(lon_raw),
    }
)
```

In `find_nearest_charger`, change the return type annotation and return the full dict:
```python
def find_nearest_charger(lat: float, lon: float, chargers: list[dict]) -> tuple[dict, float] | None:
    if not chargers:
        return None
    point = (lat, lon)
    nearest = min(chargers, key=lambda c: geodesic(point, (c["lat"], c["lon"])).miles)
    distance = round(geodesic(point, (nearest["lat"], nearest["lon"])).miles, 2)
    return nearest, distance
```

**Step 4: Update call sites**

In `cli.py`, find the block that unpacks the result (around line 180):
```python
# BEFORE:
result = find_nearest_charger(lat, lon, chargers)
if result:
    nearest_charger, distance_mi = result[0], str(result[1])

# AFTER:
result = find_nearest_charger(lat, lon, chargers)
nearest_charger_dict = None
if result:
    nearest_charger_dict, dist_float = result
    nearest_charger = nearest_charger_dict["name"]
    distance_mi = str(dist_float)
```

Check `gui.py` for the same pattern and apply the same fix (search for `find_nearest_charger`).

**Step 5: Run all tests**

```bash
pytest tests/ -v
```
Expected: All tests pass. If any test fixture uses `find_nearest_charger` with a mock that returns `("name_str", dist)`, update those mocks to return `({"name": "...", "city": "...", "state": "..."}, dist)`.

**Step 6: Commit**

```bash
git add src/itselectric/geo.py src/itselectric/cli.py src/itselectric/gui.py tests/test_geo.py
git commit -m "feat(geo): add city/state to charger dicts; find_nearest_charger returns full dict"
```

---

## Task 2: Add driver state extraction to geo.py

**Why:** The decision tree needs `driver_state` (e.g. `"CA"`), but the extracted address is a free-text string. Drivers may write the full state name ("California") or the abbreviation ("CA"). We want to handle both gracefully — only return `None` if the state is genuinely unrecognisable (misspelled or absent), not just because it was spelled out in full.

**Strategy:** Try the 2-letter abbreviation regex first. If that fails, try matching a full state name at the end of the address and look it up in a static mapping. Return `None` only if neither succeeds.

**Files:**
- Modify: `src/itselectric/geo.py`
- Modify: `tests/test_geo.py`

**Step 1: Write the failing tests**

```python
# In tests/test_geo.py

from itselectric.geo import extract_state_from_address

class TestExtractStateFromAddress:
    # 2-letter abbreviation path
    def test_standard_abbreviation(self):
        assert extract_state_from_address("123 Main St, Dallas, TX 75001") == "TX"

    def test_abbreviation_no_zip(self):
        assert extract_state_from_address("789 Pine Rd, Denver, CO") == "CO"

    def test_abbreviation_uppercase_always(self):
        assert extract_state_from_address("1 Elm St, Portland, OR 97201") == "OR"

    # Full state name path
    def test_full_state_name(self):
        assert extract_state_from_address("456 Oak Ave, Los Angeles, California 90001") == "CA"

    def test_full_state_name_no_zip(self):
        assert extract_state_from_address("99 Elm St, Austin, Texas") == "TX"

    def test_full_state_name_lowercase(self):
        assert extract_state_from_address("1 Main St, Denver, colorado") == "CO"

    def test_full_state_name_mixed_case(self):
        assert extract_state_from_address("1 Main St, Salt Lake City, Utah") == "UT"

    def test_multi_word_state(self):
        assert extract_state_from_address("5 Oak St, Charlotte, North Carolina 28201") == "NC"

    def test_multi_word_state_west_virginia(self):
        assert extract_state_from_address("10 River Rd, Charleston, West Virginia") == "WV"

    # None path — only for genuinely unrecognisable input
    def test_returns_none_for_misspelled_state(self):
        assert extract_state_from_address("123 Main St, Dallas, Texass") is None

    def test_returns_none_when_no_state(self):
        assert extract_state_from_address("123 Main Street") is None

    def test_returns_none_for_empty_string(self):
        assert extract_state_from_address("") is None

    def test_returns_none_for_none(self):
        assert extract_state_from_address(None) is None
```

**Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_geo.py::TestExtractStateFromAddress -v
```
Expected: FAIL — `extract_state_from_address` does not exist.

**Step 3: Implement in geo.py**

Add this near the top of `geo.py`, after the existing `_UNIT_RE` pattern:

```python
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
```

**Step 4: Run the tests**

```bash
pytest tests/test_geo.py::TestExtractStateFromAddress -v
```
Expected: All PASS.

**Step 5: Run all tests**

```bash
pytest tests/ -v
```
Expected: All pass.

**Step 6: Commit**

```bash
git add src/itselectric/geo.py tests/test_geo.py
git commit -m "feat(geo): add extract_state_from_address helper"
```

---

## Task 3: Implement the decision_tree.py module

**Why:** This is the core of the feature. A pure Python evaluator walks the YAML-loaded dict tree, evaluating conditions against a context dict, until it reaches a leaf with an `email_id`. Keeping it pure (no I/O, no side effects) makes it trivially testable.

**Files:**
- Create: `src/itselectric/decision_tree.py`
- Create: `tests/test_decision_tree.py`

**Step 1: Write the failing tests**

```python
# tests/test_decision_tree.py

import pytest
from itselectric.decision_tree import evaluate


class TestEvaluateLeaf:
    def test_leaf_with_email_id_returns_id(self):
        node = {"email_id": 12345}
        assert evaluate(node, {}) == 12345

    def test_leaf_with_null_email_id_returns_none(self):
        node = {"email_id": None}
        assert evaluate(node, {}) is None


class TestEvaluateConditions:
    def _branch(self, field, op, value, yes_id, no_id):
        return {
            "condition": {"field": field, "op": op, "value": value},
            "yes": {"email_id": yes_id},
            "no": {"email_id": no_id},
        }

    def test_lt_true(self):
        node = self._branch("distance_miles", "lt", 0.5, 111, 222)
        assert evaluate(node, {"distance_miles": 0.3}) == 111

    def test_lt_false(self):
        node = self._branch("distance_miles", "lt", 0.5, 111, 222)
        assert evaluate(node, {"distance_miles": 0.5}) == 222  # equal is not lt

    def test_lte_true_at_boundary(self):
        node = self._branch("distance_miles", "lte", 100, 111, 222)
        assert evaluate(node, {"distance_miles": 100}) == 111

    def test_gt_true(self):
        node = self._branch("distance_miles", "gt", 10, 111, 222)
        assert evaluate(node, {"distance_miles": 50}) == 111

    def test_gte_true_at_boundary(self):
        node = self._branch("distance_miles", "gte", 50, 111, 222)
        assert evaluate(node, {"distance_miles": 50}) == 111

    def test_eq_string(self):
        node = self._branch("driver_state", "eq", "CA", 111, 222)
        assert evaluate(node, {"driver_state": "CA"}) == 111

    def test_eq_string_mismatch(self):
        node = self._branch("driver_state", "eq", "CA", 111, 222)
        assert evaluate(node, {"driver_state": "TX"}) == 222

    def test_ne_true(self):
        node = self._branch("driver_state", "ne", "CA", 111, 222)
        assert evaluate(node, {"driver_state": "TX"}) == 111

    def test_in_true(self):
        node = self._branch("charger_city", "in", ["Los Angeles", "San Francisco"], 111, 222)
        assert evaluate(node, {"charger_city": "Los Angeles"}) == 111

    def test_in_false(self):
        node = self._branch("charger_city", "in", ["Los Angeles", "San Francisco"], 111, 222)
        assert evaluate(node, {"charger_city": "Sacramento"}) == 222


class TestEvaluateNested:
    """Validates the spec's full example tree."""

    _TREE = {
        "condition": {"field": "distance_miles", "op": "lt", "value": 0.5},
        "yes": {"email_id": 11111},  # Get General Car Info
        "no": {
            "condition": {"field": "distance_miles", "op": "lt", "value": 100},
            "yes": {
                "condition": {"field": "driver_state", "op": "eq", "value": "CA"},
                "yes": {
                    "condition": {
                        "field": "charger_city",
                        "op": "in",
                        "value": ["Los Angeles", "San Francisco"],
                    },
                    "yes": {"email_id": 67890},  # Get California Car Info
                    "no": {"email_id": 22222},   # Waitlist
                },
                "no": {"email_id": 11111},  # Get General Car Info
            },
            "no": {"email_id": 22222},  # Waitlist
        },
    }

    def test_utah_driver_150_miles_denver(self):
        """Utah driver 150 mi from Denver → Waitlist."""
        ctx = {"driver_state": "UT", "charger_state": "CO", "charger_city": "Denver", "distance_miles": 150}
        assert evaluate(self._TREE, ctx) == 22222

    def test_la_driver_15_miles_alameda(self):
        """LA driver 15 mi from Alameda charger → Get California Car Info."""
        ctx = {"driver_state": "CA", "charger_state": "CA", "charger_city": "Los Angeles", "distance_miles": 15}
        assert evaluate(self._TREE, ctx) == 67890

    def test_dallas_driver_99_miles_waco(self):
        """Dallas TX driver 99 mi from Waco → Get General Car Info."""
        ctx = {"driver_state": "TX", "charger_state": "TX", "charger_city": "Waco", "distance_miles": 99}
        assert evaluate(self._TREE, ctx) == 11111


class TestEvaluateErrors:
    def test_missing_context_field_raises(self):
        """Missing context field raises KeyError — fail loudly rather than silently wrong."""
        node = {
            "condition": {"field": "distance_miles", "op": "lt", "value": 10},
            "yes": {"email_id": 1},
            "no": {"email_id": 2},
        }
        with pytest.raises(KeyError):
            evaluate(node, {})

    def test_unknown_op_raises(self):
        """Unknown operator raises ValueError."""
        node = {
            "condition": {"field": "distance_miles", "op": "contains", "value": 5},
            "yes": {"email_id": 1},
            "no": {"email_id": 2},
        }
        with pytest.raises(ValueError, match="Unknown operator"):
            evaluate(node, {"distance_miles": 3})
```

**Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_decision_tree.py -v
```
Expected: FAIL — module does not exist.

**Step 3: Implement decision_tree.py**

```python
# src/itselectric/decision_tree.py
"""Decision tree evaluator for email routing.

A tree is a nested dict loaded from YAML. Each node is either:
  - A leaf:   {"email_id": <int | None>}
  - A branch: {"condition": {"field": str, "op": str, "value": any},
               "yes": <node>, "no": <node>}

evaluate() walks the tree and returns the email_id at the matching leaf,
or None if the leaf has a null email_id.
"""

_OPS = {
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "in": lambda a, b: a in b,
}


def evaluate(node: dict, context: dict) -> int | None:
    """
    Walk the decision tree, evaluating conditions against context.

    Args:
        node: A branch or leaf dict (see module docstring for schema).
        context: A flat dict with keys like distance_miles, driver_state,
                 charger_state, charger_city.

    Returns:
        The integer email_id at the matching leaf, or None for a null leaf.

    Raises:
        KeyError: If a required context field is missing.
        ValueError: If an operator name is unrecognised.
    """
    if "email_id" in node:
        return node["email_id"]

    cond = node["condition"]
    field = cond["field"]
    op = cond["op"]
    value = cond["value"]

    if op not in _OPS:
        raise ValueError(f"Unknown operator: {op!r}. Valid ops: {sorted(_OPS)}")

    actual = context[field]  # raises KeyError if field is absent
    branch = "yes" if _OPS[op](actual, value) else "no"
    return evaluate(node[branch], context)
```

**Step 4: Run the tests**

```bash
pytest tests/test_decision_tree.py -v
```
Expected: All PASS.

**Step 5: Run all tests**

```bash
pytest tests/ -v
```
Expected: All pass.

**Step 6: Commit**

```bash
git add src/itselectric/decision_tree.py tests/test_decision_tree.py
git commit -m "feat(decision_tree): add YAML-driven email routing evaluator"
```

---

## Task 4: Add send_email to hubspot.py

**Why:** The leaves of the decision tree reference HubSpot transactional email template IDs. We need a function to actually dispatch those emails. The HubSpot transactional email endpoint (`/marketing/v3/transactional/single-email/send`) is distinct from the CRM contact upsert — it requires the Marketing Hub transactional email add-on to be enabled on the HubSpot account.

**Files:**
- Modify: `src/itselectric/hubspot.py`
- Modify: `tests/test_hubspot.py`

**Step 1: Write the failing tests**

```python
# In tests/test_hubspot.py — add a new class

from itselectric.hubspot import send_email

class TestSendEmail:
    def _mock_send_response(self, status_code: int = 200) -> MagicMock:
        resp = MagicMock()
        resp.status_code = status_code
        resp.raise_for_status = MagicMock()
        return resp

    def test_posts_to_transactional_endpoint(self):
        """Calls the correct HubSpot transactional send endpoint."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_send_response()
            send_email(access_token="tok", to_email="driver@example.com", email_id=12345)

        url = mock_post.call_args.args[0]
        assert "/marketing/v3/transactional/single-email/send" in url

    def test_sends_correct_body(self):
        """Request body contains emailId and message.to."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_send_response()
            send_email(access_token="tok", to_email="driver@example.com", email_id=12345)

        body = mock_post.call_args.kwargs["json"]
        assert body["emailId"] == 12345
        assert body["message"]["to"] == "driver@example.com"

    def test_returns_true_on_success(self):
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_send_response()
            result = send_email(access_token="tok", to_email="d@example.com", email_id=99)
        assert result is True

    def test_returns_false_on_request_error(self):
        import requests as req
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.side_effect = req.RequestException("network error")
            result = send_email(access_token="tok", to_email="d@example.com", email_id=99)
        assert result is False
```

**Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_hubspot.py::TestSendEmail -v
```
Expected: FAIL — `send_email` does not exist.

**Step 3: Implement in hubspot.py**

Add this function to `src/itselectric/hubspot.py`:

```python
def send_email(access_token: str, to_email: str, email_id: int) -> bool:
    """
    Send a HubSpot transactional email to a contact.

    Uses the Marketing transactional send endpoint. Requires the HubSpot account
    to have the transactional email add-on enabled.

    Args:
        access_token: HubSpot Private App access token.
        to_email: Recipient email address.
        email_id: HubSpot transactional email template ID.

    Returns:
        True on success, False if the request fails.
    """
    try:
        resp = requests.post(
            f"{_BASE}/marketing/v3/transactional/single-email/send",
            headers=_headers(access_token),
            json={
                "emailId": email_id,
                "message": {"to": to_email},
            },
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"HubSpot send_email error: {e}")
        return False
```

**Step 4: Run the tests**

```bash
pytest tests/test_hubspot.py -v
```
Expected: All PASS.

**Step 5: Run all tests**

```bash
pytest tests/ -v
```
Expected: All pass.

**Step 6: Commit**

```bash
git add src/itselectric/hubspot.py tests/test_hubspot.py
git commit -m "feat(hubspot): add send_email for transactional email dispatch"
```

---

## Task 5: Add HubSpot status columns to sheets.py

**Why:** When HubSpot fails — either at contact upsert or email send — the row still gets written to the sheet, but the client has no way to know which drivers need to be retried. Two new columns ("HubSpot Contact" and "HubSpot Email") record the outcome of each operation per row. Empty means the operation wasn't attempted (HubSpot not configured, or no decision tree). Separate columns let the client filter failures independently.

**Column values:**

| Column | Values |
|---|---|
| `HubSpot Contact` | `"created"` · `"failed"` · `""` (not attempted) |
| `HubSpot Email` | `"sent"` · `"failed"` · `""` (not attempted) |

**Files:**
- Modify: `src/itselectric/sheets.py`
- Modify: `tests/test_sheets.py`

**Step 1: Write the failing tests**

```python
# In tests/test_sheets.py — add these tests

from itselectric.sheets import COLUMNS

class TestSheetColumns:
    def test_has_hubspot_contact_column(self):
        assert "HubSpot Contact" in COLUMNS

    def test_has_hubspot_email_column(self):
        assert "HubSpot Email" in COLUMNS

    def test_column_count_is_ten(self):
        assert len(COLUMNS) == 10

class TestAppendRowsIncludesHubSpotStatus:
    """append_rows must write all 10 columns including the two new HubSpot status fields."""

    def _make_row(self, contact_status="created", email_status="sent"):
        return (
            "2026-01-01", "Jane Smith", "1 Main St, Boston, MA",
            "jane@example.com", "jane2@example.com", "body text",
            "1 Main St, Boston, MA", "2.5",
            contact_status, email_status,
        )

    def test_row_includes_contact_status(self):
        from unittest.mock import MagicMock, patch
        mock_service = MagicMock()
        mock_service.spreadsheets().values().get().execute.return_value = {"values": [COLUMNS]}
        with patch("itselectric.sheets.build", return_value=mock_service):
            from itselectric.sheets import append_rows
            from unittest.mock import MagicMock as MC
            creds = MC()
            append_rows(creds, "sheet-id", "Sheet1", [self._make_row()], 5000)

        appended = mock_service.spreadsheets().values().append.call_args.kwargs["body"]["values"]
        row = appended[0]
        assert row[8] == "created"   # column I
        assert row[9] == "sent"      # column J

    def test_row_with_failed_statuses(self):
        from unittest.mock import MagicMock, patch
        mock_service = MagicMock()
        mock_service.spreadsheets().values().get().execute.return_value = {"values": [COLUMNS]}
        with patch("itselectric.sheets.build", return_value=mock_service):
            from itselectric.sheets import append_rows
            creds = MagicMock()
            append_rows(creds, "sheet-id", "Sheet1", [self._make_row("failed", "failed")], 5000)

        appended = mock_service.spreadsheets().values().append.call_args.kwargs["body"]["values"]
        row = appended[0]
        assert row[8] == "failed"
        assert row[9] == "failed"

    def test_row_with_empty_statuses(self):
        from unittest.mock import MagicMock, patch
        mock_service = MagicMock()
        mock_service.spreadsheets().values().get().execute.return_value = {"values": [COLUMNS]}
        with patch("itselectric.sheets.build", return_value=mock_service):
            from itselectric.sheets import append_rows
            creds = MagicMock()
            append_rows(creds, "sheet-id", "Sheet1", [self._make_row("", "")], 5000)

        appended = mock_service.spreadsheets().values().append.call_args.kwargs["body"]["values"]
        row = appended[0]
        assert row[8] == ""
        assert row[9] == ""
```

**Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_sheets.py::TestSheetColumns tests/test_sheets.py::TestAppendRowsIncludesHubSpotStatus -v
```
Expected: FAIL — `COLUMNS` has 8 entries, `_fmt` only unpacks 8 fields.

**Step 3: Implement in sheets.py**

Update `COLUMNS`:
```python
COLUMNS = [
    "Sent Date",
    "Name",
    "Address",
    "Email 1",
    "Email 2",
    "Content",
    "Nearest Charger",
    "Distance (mi)",
    "HubSpot Contact",   # "created" | "failed" | ""
    "HubSpot Email",     # "sent" | "failed" | ""
]
```

Update the range strings from `A:H` to `A:J` in both `get_existing_hashes` and `append_rows`:
```python
# get_existing_hashes:
range=f"'{sheet_name}'!A:J"

# append_rows:
range_name = f"'{sheet_name}'!A:J"
# and the header check:
range=f"'{sheet_name}'!A1:J1"
```

Update `_fmt` inside `append_rows` to unpack the two new fields:
```python
def _fmt(r: tuple) -> list:
    sd, nm, addr, e1, e2, body, nc, dm, hs_contact, hs_email = r
    return [sd, nm, addr, e1, e2, truncate(body, content_limit), nc, dm, hs_contact, hs_email]
```

> **Note on dedup:** `row_hash` only uses columns 0–5 (date, name, address, emails, content). The two new columns are intentionally excluded from the hash so that re-running the pipeline does not re-process rows just because a status changed. This is correct — the dedup key is the submission identity, not the HubSpot outcome.

**Step 4: Run all tests**

```bash
pytest tests/ -v
```
Expected: All pass. Any existing test that builds a row tuple will need its tuple extended with two empty strings `("", "")` at the end — fix those now.

**Step 5: Commit**

```bash
git add src/itselectric/sheets.py tests/test_sheets.py
git commit -m "feat(sheets): add HubSpot Contact and HubSpot Email status columns"
```

---

## Task 6: Wire the decision tree into cli.py

**Why:** The previous tasks built all the pieces in isolation. Now we connect them: load the decision tree YAML at startup, build the context dict after each geocode, evaluate the tree, dispatch the email, and record both HubSpot outcomes in the sheet row.

**Files:**
- Modify: `src/itselectric/cli.py`
- Modify: `tests/test_gui_pipeline.py` (or create `tests/test_cli_pipeline.py` if one doesn't exist)

**Step 1: Add config key

In `cli.py`, add `"decision_tree_file": ""` to the `_DEFAULTS` dict, and add a corresponding `--decision-tree-file` argparse argument:

```python
# In _DEFAULTS:
"decision_tree_file": "",

# In parse_args():
parser.add_argument(
    "--decision-tree-file",
    default=config.get("decision_tree_file", _DEFAULTS["decision_tree_file"]),
    metavar="PATH",
    help="Path to YAML file defining the email decision tree.",
)
```

**Step 2: Add a tree loader helper**

Add this function to `cli.py` (near `_load_config`):

```python
def _load_decision_tree(path: str) -> dict | None:
    """Load and return the decision tree dict from a YAML file, or None if path is empty."""
    if not path:
        return None
    if not os.path.exists(path):
        print(f"Warning: decision_tree_file not found at '{path}'; email routing disabled.")
        return None
    with open(path) as f:
        return yaml.safe_load(f)
```

**Step 3: Write failing integration-level tests**

Add a test file `tests/test_decision_tree_pipeline.py` that tests the context-building logic:

```python
# tests/test_decision_tree_pipeline.py
"""Tests for context building and decision tree integration in the pipeline."""

from unittest.mock import patch, MagicMock
import pytest
from itselectric.cli import _load_decision_tree, _build_tree_context


class TestLoadDecisionTree:
    def test_returns_none_for_empty_path(self, tmp_path):
        assert _load_decision_tree("") is None

    def test_returns_none_for_missing_file(self, tmp_path):
        assert _load_decision_tree(str(tmp_path / "nonexistent.yaml")) is None

    def test_loads_yaml_file(self, tmp_path):
        tree_file = tmp_path / "tree.yaml"
        tree_file.write_text("email_id: 42\n")
        result = _load_decision_tree(str(tree_file))
        assert result == {"email_id": 42}


class TestBuildTreeContext:
    def test_builds_context_with_all_fields(self):
        charger = {"name": "1 Main St, Boston, MA", "city": "Boston", "state": "MA", "lat": 42.36, "lon": -71.06}
        ctx = _build_tree_context(
            address="123 Elm St, Boston, MA 02101",
            charger_dict=charger,
            distance_miles=2.5,
        )
        assert ctx["driver_state"] == "MA"
        assert ctx["charger_state"] == "MA"
        assert ctx["charger_city"] == "Boston"
        assert ctx["distance_miles"] == 2.5

    def test_driver_state_none_when_unparseable(self):
        charger = {"name": "1 Main St, Boston, MA", "city": "Boston", "state": "MA", "lat": 42.36, "lon": -71.06}
        ctx = _build_tree_context(
            address="123 Elm Street",
            charger_dict=charger,
            distance_miles=5.0,
        )
        assert ctx["driver_state"] is None
```

**Step 4: Run the tests to confirm they fail**

```bash
pytest tests/test_decision_tree_pipeline.py -v
```
Expected: FAIL — `_build_tree_context` does not exist yet.

**Step 5: Add _build_tree_context to cli.py**

```python
# Add to cli.py imports:
from .decision_tree import evaluate as evaluate_tree
from .geo import extract_state_from_address
from .hubspot import send_email

# Add this function near _load_decision_tree:
def _build_tree_context(address: str, charger_dict: dict, distance_miles: float) -> dict:
    """Build the context dict passed to the decision tree evaluator."""
    return {
        "driver_state": extract_state_from_address(address),
        "charger_state": charger_dict["state"],
        "charger_city": charger_dict["city"],
        "distance_miles": distance_miles,
    }
```

**Step 6: Wire the tree into the main message loop**

In `main()`, load the tree after loading the config:

```python
decision_tree = _load_decision_tree(args.decision_tree_file)
```

Then restructure the message loop body to track both HubSpot statuses and include them in the sheet row. The full revised loop body for a parsed message:

```python
contact_status = ""   # "created" | "failed" | "" (not attempted)
email_status = ""     # "sent"    | "failed" | "" (not attempted)

if parsed and args.hubspot_access_token:
    contact_id = upsert_contact(
        access_token=args.hubspot_access_token,
        name=parsed["name"],
        email=parsed["email_1"],
        address=parsed["address"],
    )
    contact_status = "created" if contact_id else "failed"
    if contact_id:
        print(f"  → HubSpot contact: {contact_id}")
    else:
        print("  → HubSpot upsert failed (see error above).")

nearest_charger = ""
distance_mi = ""
nearest_charger_dict = None

if chargers:
    coords = geocode_address(parsed["address"], cache_path=args.geocache)
    if coords:
        lat, lon = coords
        result = find_nearest_charger(lat, lon, chargers)
        if result:
            nearest_charger_dict, dist_float = result
            nearest_charger = nearest_charger_dict["name"]
            distance_mi = str(dist_float)
            print(f"  → Nearest charger: {nearest_charger} ({distance_mi} mi)")
    else:
        print(f"  → Could not geocode: {parsed['address']!r}")

if decision_tree and nearest_charger_dict and args.hubspot_access_token:
    ctx = _build_tree_context(
        address=parsed["address"],
        charger_dict=nearest_charger_dict,
        distance_miles=dist_float,
    )
    try:
        email_id = evaluate_tree(decision_tree, ctx)
    except (KeyError, ValueError) as e:
        print(f"  → Decision tree error: {e}")
        email_id = None
    if email_id is not None:
        sent = send_email(
            access_token=args.hubspot_access_token,
            to_email=parsed["email_1"],
            email_id=email_id,
        )
        email_status = "sent" if sent else "failed"
        print(f"  → Email template {email_id} {'sent' if sent else 'FAILED'} → {parsed['email_1']}")

# Row tuple now has 10 fields
sheet_rows.append((
    sent_date,
    parsed["name"],
    parsed["address"],
    parsed["email_1"],
    parsed["email_2"],
    content,
    nearest_charger,
    distance_mi,
    contact_status,   # NEW
    email_status,     # NEW
))
```

For unparsed messages (where `parsed` is None), append empty strings for both status columns:
```python
sheet_rows.append((sent_date, "", "", "", "", content, "", "", "", ""))
```

**Step 7: Run all tests**

```bash
pytest tests/ -v
```
Expected: All pass.

**Step 8: Commit**

```bash
git add src/itselectric/cli.py tests/test_decision_tree_pipeline.py
git commit -m "feat(cli): wire email decision tree into pipeline"
```

---

## Task 7: Add config.example.yaml entry and verify end-to-end with fixtures

**Why:** The client needs to know how to configure this feature. The config example is the canonical reference.

**Files:**
- Modify: `config.example.yaml`

**Step 1: Update config.example.yaml**

Add the following section:

```yaml
# Path to the YAML file defining the email routing decision tree.
# When set, the pipeline evaluates the tree for each processed message
# and sends a HubSpot transactional email to the driver.
# Requires hubspot_access_token to be set.
# See docs/plans/2026-04-11-email-decision-tree.md for the tree format.
decision_tree_file: decision_tree.yaml
```

**Step 2: Create a sample decision_tree.yaml**

Create `decision_tree.example.yaml` (gitignored like config.yaml) with the full example from the top of this document.

**Step 3: Manual smoke test with fixtures**

```bash
source .venv/bin/activate
python -m itselectric.cli \
  --fixture-dir tests/fixtures/emails \
  --decision-tree-file decision_tree.example.yaml
```

With no `--hubspot-access-token`, the tree should evaluate and log the email template ID without actually sending. Check that the output contains lines like:
```
  → Email template 11111 routing: no token, skipping send
```
(You may want to add this guard — if `email_id is not None` but no token, print a note.)

**Step 4: Run all tests one final time**

```bash
pytest tests/ -v
ruff check src/ tests/
```
Expected: All 90+ tests pass, no ruff errors.

**Step 5: Commit**

```bash
git add config.example.yaml decision_tree.example.yaml
git commit -m "docs: add decision_tree_file config example and sample tree"
```

---

## HubSpot Setup Notes (for the client)

1. **Enable transactional email add-on** in HubSpot Marketing Hub settings.
2. **Create email templates** in HubSpot Marketing → Email → Create Email → Automated. Note the numeric ID from the URL.
3. **Find the email ID:** In HubSpot, go to Marketing → Email, open the template, and copy the ID from the URL (e.g. `app.hubspot.com/email/12345/edit` → ID is `12345`).
4. **Set the access token** via `hubspot_access_token` in `config.yaml` — same token used for contact upserts.

---

## What's Out of Scope

- **GUI integration:** `gui.py` does not yet have a decision tree file picker. This is a follow-up.
- **Non-US addresses:** `extract_state_from_address` assumes US state abbreviations. International support is not required.
- **Tree validation on load:** We fail at evaluation time, not load time, if the tree YAML is malformed. A schema validator could be added later.
