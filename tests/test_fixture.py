"""Tests for fixture module: loading email .txt files as Gmail message dicts."""

import pytest  # type: ignore

from itselectric.fixture import load_fixture_messages  # type: ignore
from itselectric.gmail import body_to_plain, format_sent_date, get_body_from_payload  # type: ignore


def test_load_fixture_messages_returns_one_per_file(tmp_path):
    (tmp_path / "email1.txt").write_text("hello world")
    (tmp_path / "email2.txt").write_text("another email")
    messages = load_fixture_messages(tmp_path)
    assert len(messages) == 2


def test_load_fixture_messages_body_roundtrip(tmp_path):
    """Content survives base64 encode/decode and get_body_from_payload."""
    content = "it's electric Jane Doe test body"
    (tmp_path / "email.txt").write_text(content)
    messages = load_fixture_messages(tmp_path)
    mime, text = get_body_from_payload(messages[0].get("payload", {}))
    assert mime == "text/plain"
    assert body_to_plain(mime, text) == content


def test_load_fixture_messages_date_is_parseable(tmp_path):
    """format_sent_date can extract a date string from the message."""
    (tmp_path / "email.txt").write_text("body")
    messages = load_fixture_messages(tmp_path)
    result = format_sent_date(messages[0])
    assert result != ""
    assert "UTC" in result


def test_load_fixture_messages_sorted_by_name(tmp_path):
    """Files are returned in sorted filename order."""
    (tmp_path / "b_email.txt").write_text("second")
    (tmp_path / "a_email.txt").write_text("first")
    messages = load_fixture_messages(tmp_path)
    mime0, text0 = get_body_from_payload(messages[0].get("payload", {}))
    assert body_to_plain(mime0, text0) == "first"


def test_load_fixture_messages_ignores_non_txt(tmp_path):
    """Non-.txt files are ignored."""
    (tmp_path / "email.txt").write_text("yes")
    (tmp_path / "readme.md").write_text("no")
    (tmp_path / "notes.csv").write_text("no")
    messages = load_fixture_messages(tmp_path)
    assert len(messages) == 1


def test_load_fixture_messages_empty_dir(tmp_path):
    """Empty directory returns empty list."""
    messages = load_fixture_messages(tmp_path)
    assert messages == []


def test_load_fixture_messages_missing_dir():
    """Non-existent directory raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_fixture_messages("/nonexistent/path/emails")
