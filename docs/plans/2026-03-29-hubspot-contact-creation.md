# HubSpot Contact Creation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** After extracting contact info from a form email, create or update the contact in HubSpot CRM using the Contacts API.

**Architecture:** A new `hubspot.py` module exposes a single `upsert_contact()` function using the batch upsert endpoint (`POST /crm/v3/objects/contacts/batch/upsert`) with `email` as the dedup key — one network call, no prior search needed. The CLI and GUI each gain an optional `hubspot_access_token` config key that, when present, triggers the HubSpot write after the Sheets write.

**Tech Stack:** Python `requests` (already a dependency), HubSpot CRM REST API v3 batch upsert, Private App access token auth.

**Important API note:** The batch upsert endpoint does not support partial updates when using `email` as `idProperty` — all properties must be sent every time. This is fine since we always have name/email/address from extraction.

---

### Task 1: Add `hubspot_access_token` to config and defaults

**Files:**
- Modify: `src/itselectric/cli.py` (add to `_DEFAULTS` and `parse_args`)
- Modify: `config.example.yaml` (document the new key)

**Step 1: Add default to `_DEFAULTS` dict in `cli.py`**

In `_DEFAULTS` (around line 18), add:
```python
"hubspot_access_token": "",
```

**Step 2: Add `--hubspot-access-token` argument to `parse_args` in `cli.py`**

After the `--geocache` argument block, add:
```python
parser.add_argument(
    "--hubspot-access-token",
    default=config.get("hubspot_access_token", _DEFAULTS["hubspot_access_token"]),
    metavar="TOKEN",
    help="HubSpot Private App access token. When set, creates/updates contacts in HubSpot.",
)
```

**Step 3: Document in `config.example.yaml`**

Append to the file:
```yaml
# HubSpot Private App access token. When set, creates/updates contacts in HubSpot CRM.
# Get one from: HubSpot Settings → Integrations → Private Apps
# hubspot_access_token: ""
```

**Step 4: Commit**

```bash
git add src/itselectric/cli.py config.example.yaml
git commit -m "feat(config): add hubspot_access_token config key"
```

---

### Task 2: Write the `hubspot.py` module (TDD)

**Files:**
- Create: `tests/test_hubspot.py`
- Create: `src/itselectric/hubspot.py`

**Step 1: Write the failing tests**

Create `tests/test_hubspot.py`:

```python
"""Tests for HubSpot contact upsert."""

from unittest.mock import MagicMock, patch

import pytest

from itselectric.hubspot import upsert_contact


class TestUpsertContact:
    def _mock_upsert_response(self, contact_id: str) -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = {"results": [{"id": contact_id}]}
        resp.raise_for_status = MagicMock()
        return resp

    def test_returns_contact_id_on_success(self):
        """A successful upsert returns the contact ID from the results array."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_upsert_response("101")

            contact_id = upsert_contact(
                access_token="test-token",
                name="Jane Smith",
                email="jane@example.com",
                address="123 Main St",
            )

        assert contact_id == "101"

    def test_calls_batch_upsert_endpoint(self):
        """Uses the batch upsert endpoint with email as the idProperty."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_upsert_response("101")

            upsert_contact(
                access_token="test-token",
                name="Jane Smith",
                email="jane@example.com",
                address="123 Main St",
            )

        call_args = mock_post.call_args
        assert call_args.args[0].endswith("/contacts/batch/upsert")
        body = call_args.kwargs["json"]
        assert body["inputs"][0]["idProperty"] == "email"
        assert body["inputs"][0]["id"] == "jane@example.com"

    def test_splits_name_into_first_and_last(self):
        """Full name is split on first space: 'Jane Smith' → firstname=Jane, lastname=Smith."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_upsert_response("7")

            upsert_contact(
                access_token="tok",
                name="Jane Smith",
                email="j@example.com",
                address="1 Place",
            )

        props = mock_post.call_args.kwargs["json"]["inputs"][0]["properties"]
        assert props["firstname"] == "Jane"
        assert props["lastname"] == "Smith"

    def test_single_word_name_uses_empty_lastname(self):
        """A name with no space sets lastname to empty string."""
        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.return_value = self._mock_upsert_response("8")

            upsert_contact(
                access_token="tok",
                name="Madonna",
                email="m@example.com",
                address="1 Place",
            )

        props = mock_post.call_args.kwargs["json"]["inputs"][0]["properties"]
        assert props["firstname"] == "Madonna"
        assert props["lastname"] == ""

    def test_returns_none_on_request_error(self):
        """If the API call raises an exception, return None (don't crash the pipeline)."""
        import requests as req

        with patch("itselectric.hubspot.requests.post") as mock_post:
            mock_post.side_effect = req.RequestException("network error")

            result = upsert_contact(
                access_token="tok",
                name="Jane Smith",
                email="j@example.com",
                address="1 Place",
            )

        assert result is None
```

**Step 2: Run tests to verify they fail**

```bash
source .venv/bin/activate
pytest tests/test_hubspot.py -v
```

Expected: `ModuleNotFoundError: No module named 'itselectric.hubspot'`

**Step 3: Implement `src/itselectric/hubspot.py`**

```python
"""HubSpot CRM helpers: upsert contacts via the v3 batch API."""

import requests

_BASE = "https://api.hubapi.com"


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _split_name(name: str) -> tuple[str, str]:
    """Split 'First Last' into ('First', 'Last'). Single word → ('Word', '')."""
    parts = name.strip().split(" ", 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def upsert_contact(
    access_token: str,
    name: str,
    email: str,
    address: str,
) -> str | None:
    """
    Create or update a HubSpot contact using the batch upsert endpoint.
    Uses email as the dedup key (idProperty). All properties are always sent
    since partial upserts are not supported with email as idProperty.
    Returns the contact ID, or None on error.
    """
    firstname, lastname = _split_name(name)
    try:
        resp = requests.post(
            f"{_BASE}/crm/v3/objects/contacts/batch/upsert",
            headers=_headers(access_token),
            json={
                "inputs": [
                    {
                        "id": email,
                        "idProperty": "email",
                        "properties": {
                            "email": email,
                            "firstname": firstname,
                            "lastname": lastname,
                            "address": address,
                        },
                    }
                ]
            },
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0]["id"] if results else None
    except requests.RequestException as e:
        print(f"HubSpot API error: {e}")
        return None
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_hubspot.py -v
```

Expected: 5 PASSED

**Step 5: Run full test suite to check nothing broke**

```bash
pytest tests/ -v
```

Expected: 88 passed

**Step 6: Commit**

```bash
git add src/itselectric/hubspot.py tests/test_hubspot.py
git commit -m "feat(hubspot): add upsert_contact using batch upsert endpoint"
```

---

### Task 3: Integrate HubSpot into the CLI pipeline

**Files:**
- Modify: `src/itselectric/cli.py`

**Step 1: Add the import at the top of `cli.py`**

After the existing imports, add:
```python
from .hubspot import upsert_contact
```

**Step 2: Wire HubSpot call into the message processing loop in `main()`**

In the `if parsed:` block (around line 152), after the geo lookup and before `sheet_rows.append(...)`, add:

```python
if args.hubspot_access_token:
    contact_id = upsert_contact(
        access_token=args.hubspot_access_token,
        name=parsed["name"],
        email=parsed["email_1"],
        address=parsed["address"],
    )
    if contact_id:
        print(f"  → HubSpot contact: {contact_id}")
    else:
        print("  → HubSpot upsert failed (see error above).")
```

**Step 3: Write a CLI integration test**

Add to `tests/test_integration.py` inside `class TestFullPipeline`:

```python
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
```

**Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all passing

**Step 5: Commit**

```bash
git add src/itselectric/cli.py tests/test_integration.py
git commit -m "feat(cli): call upsert_contact when hubspot_access_token is configured"
```

---

### Task 4: Integrate HubSpot into the GUI

**Files:**
- Modify: `src/itselectric/gui.py`

**Step 1: Find the relevant spots in `gui.py`**

```bash
grep -n "spreadsheet_id\|fixture_dir\|geocache\|chargers\|extract_parsed" src/itselectric/gui.py
```

This shows you where config keys are read and where the processing loop is.

**Step 2: Add `hubspot_access_token` to the GUI config reading**

Find the block where `spreadsheet_id` is pulled from config. Add next to it:
```python
hubspot_access_token = config.get("hubspot_access_token", "")
```

**Step 3: Add import and HubSpot call in the GUI processing loop**

Add at top of `gui.py` with other imports:
```python
from .hubspot import upsert_contact
```

In the loop where `extract_parsed` is called and returns a result, add the same guard as CLI:
```python
if hubspot_access_token:
    contact_id = upsert_contact(
        access_token=hubspot_access_token,
        name=parsed["name"],
        email=parsed["email_1"],
        address=parsed["address"],
    )
    status = f"HubSpot contact: {contact_id}" if contact_id else "HubSpot upsert failed"
    # append `status` to whatever log/output widget the GUI uses
```

**Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all passing

**Step 5: Commit**

```bash
git add src/itselectric/gui.py
git commit -m "feat(gui): call upsert_contact when hubspot_access_token is configured"
```

---

### Task 5: Final verification

**Step 1: Run the full test suite**

```bash
source .venv/bin/activate
pytest tests/ -v
```

Expected: 88+ passed, 0 failed

**Step 2: Smoke-test with fixture mode + a real token (manual)**

```bash
python -m itselectric.cli \
  --fixture-dir tests/fixtures/emails \
  --hubspot-access-token YOUR_TOKEN_HERE
```

Expected output includes lines like `→ HubSpot contact: 12345678`

**Step 3: Final commit if anything was missed**

```bash
git add -p
git commit -m "docs: finalize hubspot integration config and docs"
```

---

## Key Design Decisions

- **Batch upsert over search-then-create** — one network call instead of two; HubSpot handles the create-vs-update logic server-side using `email` as `idProperty`.
- **All properties sent every time** — required by the API when using `email` as `idProperty` (partial upserts not supported).
- **`email_1` is used as the HubSpot dedup key** — this is the email extracted from Gmail headers, the most reliable field.
- **Errors are non-fatal** — `upsert_contact` returns `None` on failure and prints a message; the pipeline continues to write to Sheets regardless.
- **No new dependency** — `requests` is already in `requirements.txt`.
