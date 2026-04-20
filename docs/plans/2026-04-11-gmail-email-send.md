# Gmail Email Send Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace HubSpot transactional email sending with Gmail API sends using local plain-text templates, with the decision tree selecting templates by name rather than HubSpot IDs.

**Architecture:** Email templates are `.txt` files in a configurable directory, with the first line as the subject and the remainder as the body (supports `{name}`/`{address}` substitution). The decision tree leaf key changes from `email_id` (HubSpot integer) to `template` (template filename without extension). `gmail.py` gains `load_template` and `send_email`; the HubSpot `send_email` is removed entirely.

**Tech Stack:** Gmail API (`users.messages.send`), `email.mime.text.MIMEText`, existing Google OAuth credentials

---

### Task 1: Remove send_email from hubspot.py and its tests

**Files:**
- Modify: `src/itselectric/hubspot.py`
- Modify: `tests/test_hubspot.py`

**Step 1: Delete `send_email` from hubspot.py**

Remove everything from line 61 onward (the `send_email` function). Final file ends after `upsert_contact`.

**Step 2: Delete `TestSendEmail` from test_hubspot.py**

Remove the entire `TestSendEmail` class (the 4 tests for `send_email`). Also remove `send_email` from the import on line 5 — it should read:
```python
from itselectric.hubspot import upsert_contact
```

**Step 3: Run tests to verify they pass**

```bash
uv run --extra dev pytest tests/test_hubspot.py -v
```
Expected: 5 passed (only `TestUpsertContact` tests remain)

**Step 4: Commit**
```bash
git add src/itselectric/hubspot.py tests/test_hubspot.py
git commit -m "refactor(hubspot): remove send_email, replacing with gmail send"
```

---

### Task 2: Add gmail.send scope to auth.py

**Files:**
- Modify: `src/itselectric/auth.py:11-14`

**Step 1: Add the send scope**

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
]
```

**Step 2: Note for the operator**

Adding a new scope invalidates the existing `token.json`. After deploying, delete `token.json` and re-run the pipeline to trigger a fresh OAuth consent screen. This is a one-time step.

**Step 3: Run full test suite (no auth tests touch SCOPES directly)**

```bash
uv run --extra dev pytest tests/ -q
```
Expected: all passing

**Step 4: Commit**
```bash
git add src/itselectric/auth.py
git commit -m "feat(auth): add gmail.send scope for outbound email"
```

---

### Task 3: Add load_template and send_email to gmail.py

**Files:**
- Modify: `src/itselectric/gmail.py`
- Modify: `tests/test_gmail.py`

**Template file format:**
```
Subject line goes here
<blank line>
Body text goes here.
Can span multiple lines.
Supports {name} and {address} substitution.
```

**Step 1: Write the failing tests**

Add to `tests/test_gmail.py`:

```python
import base64
import email as email_lib
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch


class TestLoadTemplate:
    def test_returns_subject_and_body(self, tmp_path):
        t = tmp_path / "welcome.txt"
        t.write_text("Welcome to It's Electric\n\nHi {name}, thanks for signing up!")
        from itselectric.gmail import load_template
        subject, body = load_template("welcome", str(tmp_path))
        assert subject == "Welcome to It's Electric"
        assert body == "Hi {name}, thanks for signing up!"

    def test_raises_on_missing_template(self, tmp_path):
        from itselectric.gmail import load_template
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent", str(tmp_path))

    def test_subject_is_first_line(self, tmp_path):
        t = tmp_path / "t.txt"
        t.write_text("My Subject\n\nMy body")
        from itselectric.gmail import load_template
        subject, _ = load_template("t", str(tmp_path))
        assert subject == "My Subject"

    def test_body_excludes_subject_line(self, tmp_path):
        t = tmp_path / "t.txt"
        t.write_text("Subject\n\nLine 1\nLine 2")
        from itselectric.gmail import load_template
        _, body = load_template("t", str(tmp_path))
        assert body == "Line 1\nLine 2"


class TestSendEmail:
    def _mock_service(self):
        svc = MagicMock()
        svc.users().messages().send().execute.return_value = {"id": "msg123"}
        return svc

    def test_returns_true_on_success(self):
        creds = MagicMock()
        with patch("itselectric.gmail.build", return_value=self._mock_service()):
            from itselectric.gmail import send_email
            assert send_email(creds, "to@example.com", "Subject", "Body") is True

    def test_returns_false_on_http_error(self):
        from googleapiclient.errors import HttpError
        creds = MagicMock()
        svc = MagicMock()
        svc.users().messages().send().execute.side_effect = HttpError(
            MagicMock(status=500), b"error"
        )
        with patch("itselectric.gmail.build", return_value=svc):
            from itselectric.gmail import send_email
            assert send_email(creds, "to@example.com", "Subject", "Body") is False

    def test_sends_to_correct_address(self):
        creds = MagicMock()
        captured = {}
        svc = self._mock_service()
        def capture_send(userId, body):
            captured["raw"] = body["raw"]
            return svc.users().messages().send()
        svc.users().messages().send = capture_send
        with patch("itselectric.gmail.build", return_value=svc):
            from itselectric.gmail import send_email
            send_email(creds, "driver@example.com", "Hello", "Body text")
        raw = base64.urlsafe_b64decode(captured["raw"])
        msg = email_lib.message_from_bytes(raw)
        assert msg["to"] == "driver@example.com"

    def test_subject_in_message(self):
        creds = MagicMock()
        captured = {}
        svc = self._mock_service()
        def capture_send(userId, body):
            captured["raw"] = body["raw"]
            return svc.users().messages().send()
        svc.users().messages().send = capture_send
        with patch("itselectric.gmail.build", return_value=svc):
            from itselectric.gmail import send_email
            send_email(creds, "x@example.com", "My Subject", "Body")
        raw = base64.urlsafe_b64decode(captured["raw"])
        msg = email_lib.message_from_bytes(raw)
        assert msg["subject"] == "My Subject"
```

Also add `import pytest` at the top of `tests/test_gmail.py` if not already there.

**Step 2: Run tests to verify they fail**

```bash
uv run --extra dev pytest tests/test_gmail.py -k "TestLoadTemplate or TestSendEmail" -v
```
Expected: FAIL with `ImportError` (functions not yet defined)

**Step 3: Implement load_template and send_email in gmail.py**

Add to the bottom of `src/itselectric/gmail.py`:

```python
import os
from email.mime.text import MIMEText

from googleapiclient.errors import HttpError  # type: ignore


def load_template(template_name: str, template_dir: str) -> tuple[str, str]:
    """
    Load an email template by name from template_dir.

    Template file format:
        Subject line
        <blank line>
        Body text (may span multiple lines, supports {name}/{address} substitution)

    Returns (subject, body). Raises FileNotFoundError if template doesn't exist.
    """
    path = os.path.join(template_dir, f"{template_name}.txt")
    with open(path) as f:
        content = f.read()
    parts = content.split("\n\n", 1)
    subject = parts[0].strip()
    body = parts[1].strip() if len(parts) > 1 else ""
    return subject, body


def send_email(creds: Credentials, to_email: str, subject: str, body: str) -> bool:
    """
    Send a plain-text email via the authenticated Gmail account.

    Returns True on success, False on error.
    """
    import base64

    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    service = build("gmail", "v1", credentials=creds)
    try:
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except HttpError as e:
        print(f"Gmail send error: {e}")
        return False
```

Note: `base64` is already imported at the top of `gmail.py` — move the `import base64` inside `send_email` out to the top-level import or use the existing one.

**Step 4: Run tests to verify they pass**

```bash
uv run --extra dev pytest tests/test_gmail.py -v
```
Expected: all passing

**Step 5: Commit**
```bash
git add src/itselectric/gmail.py tests/test_gmail.py
git commit -m "feat(gmail): add load_template and send_email"
```

---

### Task 4: Update decision_tree.py to use `template` leaf key

**Files:**
- Modify: `src/itselectric/decision_tree.py`
- Modify: `tests/test_decision_tree.py`

The leaf key changes from `email_id` (int | None) to `template` (str | None). This is the only change to the evaluator — all condition/branch logic stays identical.

**Step 1: Update tests to use `template` key**

In `tests/test_decision_tree.py`, replace every instance of `"email_id"` with `"template"` and every integer leaf value with a string template name. Example:

```python
# Old
node = {"email_id": 12345}
assert evaluate(node, {}) == 12345

# New
node = {"template": "general_car_info"}
assert evaluate(node, {}) == "general_car_info"
```

Apply this rename throughout the file. The `_TREE` nested fixture should become:
```python
_TREE = {
    "condition": {"field": "distance_miles", "op": "lt", "value": 0.5},
    "then": {"template": "general_car_info"},
    "else": {
        "condition": {"field": "distance_miles", "op": "lt", "value": 100},
        "then": {
            "condition": {"field": "driver_state", "op": "eq", "value": "CA"},
            "then": {
                "condition": {
                    "field": "charger_city",
                    "op": "in",
                    "value": ["Los Angeles", "San Francisco"],
                },
                "then": {"template": "california_car_info"},
                "else": {"template": "waitlist"},
            },
            "else": {"template": "general_car_info"},
        },
        "else": {"template": "waitlist"},
    },
}
```

And update the three scenario assertions:
```python
assert evaluate(self._TREE, ctx) == "waitlist"        # Utah
assert evaluate(self._TREE, ctx) == "california_car_info"  # LA
assert evaluate(self._TREE, ctx) == "general_car_info"     # Dallas
```

**Step 2: Run tests to confirm they fail**

```bash
uv run --extra dev pytest tests/test_decision_tree.py -v
```
Expected: FAIL — `evaluate` still looks for `email_id`

**Step 3: Update decision_tree.py**

In `src/itselectric/decision_tree.py`, change:
```python
# Old
def evaluate(node: dict, context: dict) -> int | None:
    if "email_id" in node:
        return node["email_id"]

# New
def evaluate(node: dict, context: dict) -> str | None:
    if "template" in node:
        return node["template"]
```

**Step 4: Run tests to verify they pass**

```bash
uv run --extra dev pytest tests/test_decision_tree.py -v
```
Expected: all passing

**Step 5: Commit**
```bash
git add src/itselectric/decision_tree.py tests/test_decision_tree.py
git commit -m "feat(decision_tree): replace email_id leaf with template name"
```

---

### Task 5: Wire gmail send into cli.py

**Files:**
- Modify: `src/itselectric/cli.py`
- Modify: `tests/test_decision_tree_pipeline.py`

**Step 1: Update imports in cli.py**

Replace:
```python
from .hubspot import send_email, upsert_contact
```
With:
```python
from .gmail import load_template, send_email
from .hubspot import upsert_contact
```

**Step 2: Add `template_dir` to `_DEFAULTS` and argparse**

In `_DEFAULTS`:
```python
"template_dir": "",
```

In `parse_args`, add after the `--decision-tree-file` argument:
```python
parser.add_argument(
    "--template-dir",
    default=config.get("template_dir", _DEFAULTS["template_dir"]),
    metavar="DIR",
    help="Directory containing email template .txt files.",
)
```

**Step 3: Update the decision tree block in main()**

Replace the current `send_email` call (which used HubSpot `email_id`) with the Gmail send:

```python
if (
    decision_tree
    and nearest_charger_dict
    and dist_float
    and parsed
    and args.template_dir
    and creds
):
    ctx = _build_tree_context(
        address=parsed["address"],
        charger_dict=nearest_charger_dict,
        distance_miles=dist_float,
    )
    try:
        template_name = evaluate_tree(decision_tree, ctx)
    except (KeyError, ValueError) as e:
        print(f"  → Decision tree error: {e}")
        template_name = None
    if template_name is not None:
        try:
            subject, body = load_template(template_name, args.template_dir)
            body = body.format_map({"name": parsed["name"], "address": parsed["address"]})
        except FileNotFoundError:
            print(f"  → Template '{template_name}' not found in {args.template_dir}")
            template_name = None
    if template_name is not None:
        sent = send_email(creds, parsed["email_1"], subject, body)
        email_status = "sent" if sent else "failed"
        print(
            f"  → Email '{template_name}' "
            f"{'sent' if sent else 'FAILED'} → {parsed['email_1']}"
        )
```

Also remove the `and args.hubspot_access_token` gate from the decision tree condition — email routing now depends on `template_dir` and `creds` instead.

**Step 4: Run full tests**

```bash
uv run --extra dev pytest tests/ -q
```
Expected: all passing

**Step 5: Commit**
```bash
git add src/itselectric/cli.py
git commit -m "feat(cli): send emails via gmail using template files"
```

---

### Task 6: Wire gmail send into gui.py

**Files:**
- Modify: `src/itselectric/gui.py`

Bring `gui.py` to full parity with `cli.py` — all changes mirror Task 5 exactly.

**Step 1: Update imports inside `_run_pipeline`**

Replace:
```python
from itselectric.hubspot import send_email, upsert_contact
```
With:
```python
from itselectric.gmail import load_template, send_email
from itselectric.hubspot import upsert_contact
```

**Step 2: Add `template_dir` config key reading**

After the existing config key reads, add:
```python
template_dir = config.get("template_dir", "").strip()
```

**Step 3: Replace the decision tree block**

Replace the existing `send_email(access_token=..., ...)` block with the same gmail send block from Task 5, using `template_dir`, `creds`, and local variable names (no `args.` prefix):

```python
if (
    decision_tree
    and nearest_charger_dict
    and dist_float
    and parsed
    and template_dir
    and creds
):
    ctx = {
        "driver_state": extract_state_from_address(parsed["address"]),
        "charger_state": nearest_charger_dict["state"],
        "charger_city": nearest_charger_dict["city"],
        "distance_miles": dist_float,
    }
    try:
        template_name = evaluate_tree(decision_tree, ctx)
    except (KeyError, ValueError) as e:
        print(f"  → Decision tree error: {e}")
        template_name = None
    if template_name is not None:
        try:
            subject, body = load_template(template_name, template_dir)
            body = body.format_map({"name": parsed["name"], "address": parsed["address"]})
        except FileNotFoundError:
            print(f"  → Template '{template_name}' not found in {template_dir}")
            template_name = None
    if template_name is not None:
        sent = send_email(creds, parsed["email_1"], subject, body)
        email_status = "sent" if sent else "failed"
        print(
            f"  → Email '{template_name}' "
            f"{'sent' if sent else 'FAILED'} → {parsed['email_1']}"
        )
```

**Step 4: Run full tests**

```bash
uv run --extra dev pytest tests/ -q
```
Expected: all passing

**Step 5: Commit**
```bash
git add src/itselectric/gui.py
git commit -m "feat(gui): send emails via gmail using template files"
```

---

### Task 7: Update example files and create sample templates

**Files:**
- Modify: `config.example.yaml`
- Modify: `decision_tree.example.yaml`
- Create: `email_templates/general_car_info.txt`
- Create: `email_templates/california_car_info.txt`
- Create: `email_templates/waitlist.txt`

**Step 1: Update config.example.yaml**

Replace the `decision_tree_file` comment block to also document `template_dir`:
```yaml
# Path to YAML file defining the email routing decision tree.
# decision_tree_file: decision_tree.yaml

# Directory containing email template .txt files.
# Each file: first line = subject, blank line, then body.
# Supports {name} and {address} substitution in the body.
# template_dir: email_templates
```

**Step 2: Update decision_tree.example.yaml**

Replace all `email_id:` leaves with `template:` string names matching the sample templates:
```yaml
then:
  template: general_car_info
# ...
then:
  template: california_car_info
else:
  template: waitlist
```

**Step 3: Create sample template files**

`email_templates/general_car_info.txt`:
```
Thanks for your interest in It's Electric!

Hi {name},

Thanks for reaching out about EV charging at your address ({address}).

We'd love to learn more about your vehicle so we can get you set up with the right charging solution.

— The It's Electric Team
```

`email_templates/california_car_info.txt`:
```
EV Charging in California — Let's Get You Set Up

Hi {name},

Great news — we have chargers near your area ({address}) and we're ready to help California drivers get set up quickly.

We'll be in touch shortly with next steps.

— The It's Electric Team
```

`email_templates/waitlist.txt`:
```
You're on the It's Electric waitlist!

Hi {name},

Thanks for your interest! We don't have a charger near {address} yet, but you're on our waitlist and we'll reach out as soon as we expand to your area.

— The It's Electric Team
```

**Step 4: Add email_templates/ to .gitignore or keep it tracked**

Since these are content files the client edits, keep them tracked in git (do not add to .gitignore).

**Step 5: Commit**
```bash
git add config.example.yaml decision_tree.example.yaml email_templates/
git commit -m "docs: add gmail email template examples and update config docs"
```
