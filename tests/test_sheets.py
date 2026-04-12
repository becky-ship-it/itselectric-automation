"""Tests for sheet hashing, deduplication, and column structure."""

from unittest.mock import MagicMock, patch

from itselectric.sheets import COLUMNS, append_rows, row_hash, truncate


def _make_row(contact_status="created", email_status="sent"):
    return (
        "2026-01-01", "Jane Smith", "1 Main St, Boston, MA",
        "jane@example.com", "jane2@example.com", "body text",
        "1 Main St, Boston, MA", "2.5",
        contact_status, email_status,
    )


def _mock_service_with_header():
    """Service mock where the sheet already has a header row."""
    mock_service = MagicMock()
    mock_service.spreadsheets().values().get().execute.return_value = {"values": [COLUMNS]}
    return mock_service


class TestSheetColumns:
    def test_has_hubspot_contact_column(self):
        assert "HubSpot Contact" in COLUMNS

    def test_has_hubspot_email_column(self):
        assert "HubSpot Email" in COLUMNS

    def test_column_count_is_ten(self):
        assert len(COLUMNS) == 10


class TestAppendRowsHubSpotStatus:
    def test_row_includes_contact_and_email_status(self):
        with patch("itselectric.sheets.build", return_value=_mock_service_with_header()) as _:
            mock_service = _mock_service_with_header()
            with patch("itselectric.sheets.build", return_value=mock_service):
                append_rows(MagicMock(), "sheet-id", "Sheet1", [_make_row()], 5000)

        appended = mock_service.spreadsheets().values().append.call_args.kwargs["body"]["values"]
        row = appended[0]
        assert row[8] == "created"
        assert row[9] == "sent"

    def test_failed_statuses_written(self):
        mock_service = _mock_service_with_header()
        with patch("itselectric.sheets.build", return_value=mock_service):
            append_rows(MagicMock(), "sheet-id", "Sheet1", [_make_row("failed", "failed")], 5000)

        row = mock_service.spreadsheets().values().append.call_args.kwargs["body"]["values"][0]
        assert row[8] == "failed"
        assert row[9] == "failed"

    def test_empty_statuses_written(self):
        mock_service = _mock_service_with_header()
        with patch("itselectric.sheets.build", return_value=mock_service):
            append_rows(MagicMock(), "sheet-id", "Sheet1", [_make_row("", "")], 5000)

        row = mock_service.spreadsheets().values().append.call_args.kwargs["body"]["values"][0]
        assert row[8] == ""
        assert row[9] == ""

    def test_row_hash_excludes_hubspot_columns(self):
        """Dedup hash must not change when HubSpot status columns differ."""
        row_created = list(_make_row("created", "sent"))
        row_failed = list(_make_row("failed", "failed"))
        assert row_hash(row_created, 5000) == row_hash(row_failed, 5000)

LIMIT = 5000


def test_truncate_short():
    assert truncate("hello", LIMIT) == "hello"


def test_truncate_long():
    long = "x" * 6000
    result = truncate(long, LIMIT)
    assert len(result) == LIMIT
    assert result.endswith("...")


def test_truncate_none():
    assert truncate(None, LIMIT) == ""


def test_truncate_strips_whitespace():
    assert truncate("  hi  ", LIMIT) == "hi"


def test_row_hash_parsed_row_consistent():
    row = ["2024-01-01", "John", "123 Main", "a@b.com", "c@d.com", "some content"]
    h1 = row_hash(row, LIMIT)
    h2 = row_hash(row, LIMIT)
    assert h1 == h2


def test_row_hash_parsed_ignores_content():
    """Parsed rows deduplicate on fields, not content."""
    row1 = ["2024-01-01", "John", "123 Main", "a@b.com", "c@d.com", "content A"]
    row2 = ["2024-01-01", "John", "123 Main", "a@b.com", "c@d.com", "content B"]
    assert row_hash(row1, LIMIT) == row_hash(row2, LIMIT)


def test_row_hash_unparsed_uses_content():
    """Unparsed rows (no name/address/emails) deduplicate on (date, content)."""
    row1 = ["2024-01-01", "", "", "", "", "content A"]
    row2 = ["2024-01-01", "", "", "", "", "content B"]
    assert row_hash(row1, LIMIT) != row_hash(row2, LIMIT)


def test_row_hash_parsed_vs_unparsed_differ():
    parsed = ["2024-01-01", "John", "123 Main", "a@b.com", "c@d.com", "body"]
    unparsed = ["2024-01-01", "", "", "", "", "body"]
    assert row_hash(parsed, LIMIT) != row_hash(unparsed, LIMIT)


def test_row_hash_short_row():
    """Should not raise on rows with fewer than 6 columns."""
    row_hash(["2024-01-01"], LIMIT)
    row_hash([], LIMIT)
