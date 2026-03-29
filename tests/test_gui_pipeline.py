"""
Tests for gui._run_pipeline and _LogWriter.

Key behaviors under test (from the recent bug fix):
    - _on_done is always scheduled via self.after(), even when an exception occurs
    - sys.stdout is always restored in the finally block
    - success=False when the pipeline raises; success=True only after full completion
    - Correct status messages for each outcome branch
"""

import sys
from unittest.mock import MagicMock, patch

import yaml

# ---------------------------------------------------------------------------
# Stub customtkinter so itselectric.gui can be imported without a display.
# CTk must be a real Python class (Python can't inherit from a MagicMock instance).
# ---------------------------------------------------------------------------
if "customtkinter" not in sys.modules:
    _ctk_stub = MagicMock()

    class _MockCTk:
        pass

    _ctk_stub.CTk = _MockCTk
    sys.modules["customtkinter"] = _ctk_stub

from itselectric.gui import EmailSheetsApp, _LogWriter  # noqa: E402 — must follow stub

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_config(tmp_path, extra=None):
    """Write a minimal config.yaml and return its path."""
    cfg = {"label": "INBOX", "max_messages": 1}
    if extra:
        cfg.update(extra)
    p = tmp_path / "config.yaml"
    p.write_text(yaml.dump(cfg))
    return str(p)


class _FakeHttpError(Exception):
    """Stands in for googleapiclient.errors.HttpError in tests."""


def _run(self_mock, yaml_path, *, messages=None, existing=None):
    """
    Call EmailSheetsApp._run_pipeline with all itselectric internals mocked.
    Returns the mock_sheets so callers can assert on append_rows etc.
    """
    mock_errors = MagicMock()
    mock_errors.HttpError = _FakeHttpError

    mock_auth = MagicMock()

    mock_gmail = MagicMock()
    mock_gmail.fetch_messages.return_value = messages or []
    mock_gmail.get_body_from_payload.return_value = (None, None)
    mock_gmail.format_sent_date.return_value = "2024-01-01 00:00:00 UTC"

    mock_extract = MagicMock()
    mock_extract.extract_parsed.return_value = None

    mock_sheets = MagicMock()
    mock_sheets.get_existing_hashes.return_value = existing if existing is not None else set()
    mock_sheets.row_hash.return_value = "deadbeef"

    with patch.dict(
        "sys.modules",
        {
            "googleapiclient.errors": mock_errors,
            "itselectric.auth": mock_auth,
            "itselectric.gmail": mock_gmail,
            "itselectric.extract": mock_extract,
            "itselectric.sheets": mock_sheets,
            "itselectric.hubspot": MagicMock(),
        },
    ):
        EmailSheetsApp._run_pipeline(self_mock, yaml_path)

    return mock_sheets


def _on_done_args(self_mock):
    """
    Extract (success, message) from the self.after(0, self._on_done, ...) call.
    Raises AssertionError if _on_done was never scheduled.
    """
    for call in self_mock.after.call_args_list:
        args = call[0]
        if len(args) >= 4 and args[1] is self_mock._on_done:
            return args[2], args[3]
    raise AssertionError("_on_done was never scheduled via self.after()")


# ── _LogWriter ─────────────────────────────────────────────────────────────────


class TestLogWriter:
    def test_write_calls_callback_with_text(self):
        received = []
        writer = _LogWriter(received.append)
        writer.write("hello world")
        assert received == ["hello world"]

    def test_write_strips_trailing_newline(self):
        received = []
        writer = _LogWriter(received.append)
        writer.write("hello\n")
        assert received == ["hello"]

    def test_write_skips_blank_text(self):
        received = []
        writer = _LogWriter(received.append)
        writer.write("   \n   ")
        assert received == []

    def test_write_skips_empty_string(self):
        received = []
        writer = _LogWriter(received.append)
        writer.write("")
        assert received == []

    def test_flush_does_not_raise(self):
        writer = _LogWriter(lambda t: None)
        writer.flush()  # must not raise


# ── _run_pipeline: completion guarantees ───────────────────────────────────────


class TestRunPipelineCompletion:
    def test_on_done_called_on_success(self, tmp_path):
        """_on_done is scheduled after a normal successful run."""
        self_mock = MagicMock()
        _run(self_mock, _make_config(tmp_path))
        _on_done_args(self_mock)  # raises if not found

    def test_on_done_called_when_get_credentials_raises(self, tmp_path):
        """_on_done is scheduled even if an exception fires mid-pipeline."""
        self_mock = MagicMock()

        mock_errors = MagicMock()
        mock_errors.HttpError = _FakeHttpError
        mock_auth = MagicMock()
        mock_auth.get_credentials.side_effect = RuntimeError("no network")

        with patch.dict(
            "sys.modules",
            {
                "googleapiclient.errors": mock_errors,
                "itselectric.auth": mock_auth,
                "itselectric.gmail": MagicMock(),
                "itselectric.extract": MagicMock(),
                "itselectric.sheets": MagicMock(),
            },
        ):
            EmailSheetsApp._run_pipeline(self_mock, _make_config(tmp_path))

        success, message = _on_done_args(self_mock)
        assert success is False
        assert "no network" in message

    def test_success_false_when_config_file_missing(self, tmp_path):
        """Non-existent config file → success=False with a descriptive message."""
        self_mock = MagicMock()
        _run(self_mock, str(tmp_path / "no_such_file.yaml"))
        success, message = _on_done_args(self_mock)
        assert success is False
        assert "no_such_file.yaml" in message or "not found" in message.lower()

    def test_stdout_restored_after_success(self, tmp_path):
        """sys.stdout must be the original object after a normal run."""
        original = sys.stdout
        self_mock = MagicMock()
        _run(self_mock, _make_config(tmp_path))
        assert sys.stdout is original

    def test_stdout_restored_after_exception(self, tmp_path):
        """sys.stdout must be restored even when the pipeline raises."""
        original = sys.stdout
        self_mock = MagicMock()

        mock_errors = MagicMock()
        mock_errors.HttpError = _FakeHttpError
        mock_auth = MagicMock()
        mock_auth.get_credentials.side_effect = RuntimeError("boom")

        with patch.dict(
            "sys.modules",
            {
                "googleapiclient.errors": mock_errors,
                "itselectric.auth": mock_auth,
                "itselectric.gmail": MagicMock(),
                "itselectric.extract": MagicMock(),
                "itselectric.sheets": MagicMock(),
            },
        ):
            EmailSheetsApp._run_pipeline(self_mock, _make_config(tmp_path))

        assert sys.stdout is original


# ── _run_pipeline: message content ─────────────────────────────────────────────


class TestRunPipelineMessages:
    def test_preview_message_when_spreadsheet_id_empty(self, tmp_path):
        """Empty spreadsheet_id → 'Preview complete' message, success=True."""
        self_mock = MagicMock()
        # Two messages, no spreadsheet_id
        _run(
            self_mock,
            _make_config(tmp_path, {"spreadsheet_id": ""}),
            messages=[
                {"internalDate": "0", "payload": {}},
                {"internalDate": "0", "payload": {}},
            ],
        )
        success, message = _on_done_args(self_mock)
        assert success is True
        assert "Preview complete" in message
        assert "2" in message

    def test_success_when_new_rows_appended(self, tmp_path):
        """New rows are appended when none already exist on the sheet."""
        self_mock = MagicMock()
        mock_sheets = _run(
            self_mock,
            _make_config(tmp_path, {"spreadsheet_id": "sheet_abc"}),
            messages=[{"internalDate": "0", "payload": {}}],
            existing=set(),
        )
        success, message = _on_done_args(self_mock)
        assert success is True
        mock_sheets.append_rows.assert_called_once()

    def test_skips_all_duplicate_rows(self, tmp_path):
        """When all rows already exist on the sheet, append_rows is not called."""
        self_mock = MagicMock()
        # row_hash mock returns "deadbeef"; put that in existing so dedup fires
        mock_sheets = _run(
            self_mock,
            _make_config(tmp_path, {"spreadsheet_id": "sheet_abc"}),
            messages=[{"internalDate": "0", "payload": {}}],
            existing={"deadbeef"},
        )
        success, message = _on_done_args(self_mock)
        assert success is True
        mock_sheets.append_rows.assert_not_called()
        assert "already on sheet" in message

    def test_no_messages_found(self, tmp_path):
        """Empty message list with spreadsheet_id → 'No messages found'."""
        self_mock = MagicMock()
        _run(
            self_mock,
            _make_config(tmp_path, {"spreadsheet_id": "sheet_abc"}),
            messages=[],
        )
        success, message = _on_done_args(self_mock)
        assert success is True
        assert "No messages found" in message
