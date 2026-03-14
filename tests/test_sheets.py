"""Tests for sheet hashing and deduplication logic."""

from itselectric.sheets import row_hash, truncate

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
