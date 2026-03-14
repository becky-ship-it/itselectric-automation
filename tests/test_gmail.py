"""Tests for gmail module: body decoding, HTML stripping, date formatting."""

import base64

from itselectric.gmail import body_to_plain, format_sent_date, get_body_from_payload, html_to_plain


def _enc(text: str) -> str:
    """Base64url-encode a string the same way Gmail does."""
    return base64.urlsafe_b64encode(text.encode()).decode()


# ── get_body_from_payload ──────────────────────────────────────────────────────


class TestGetBodyFromPayload:
    def test_single_part_plain(self):
        payload = {"mimeType": "text/plain", "body": {"data": _enc("hello world")}}
        mime, text = get_body_from_payload(payload)
        assert mime == "text/plain"
        assert text == "hello world"

    def test_single_part_html(self):
        payload = {"mimeType": "text/html", "body": {"data": _enc("<b>hi</b>")}}
        mime, text = get_body_from_payload(payload)
        assert mime == "text/html"
        assert text == "<b>hi</b>"

    def test_empty_payload_returns_none(self):
        mime, text = get_body_from_payload({})
        assert mime is None
        assert text is None

    def test_body_with_no_data_returns_none(self):
        payload = {"mimeType": "text/plain", "body": {}}
        mime, text = get_body_from_payload(payload)
        assert mime is None
        assert text is None

    def test_multipart_prefers_html_over_plain(self):
        payload = {
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _enc("plain text")}},
                {"mimeType": "text/html", "body": {"data": _enc("<p>html</p>")}},
            ]
        }
        mime, text = get_body_from_payload(payload)
        assert mime == "text/html"
        assert text == "<p>html</p>"

    def test_multipart_falls_back_to_plain_when_no_html(self):
        payload = {
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _enc("only plain")}},
            ]
        }
        mime, text = get_body_from_payload(payload)
        assert mime == "text/plain"
        assert text == "only plain"

    def test_nested_multipart_finds_html(self):
        payload = {
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {"mimeType": "text/plain", "body": {"data": _enc("inner plain")}},
                        {"mimeType": "text/html", "body": {"data": _enc("<p>inner html</p>")}},
                    ],
                }
            ]
        }
        mime, text = get_body_from_payload(payload)
        assert mime == "text/html"
        assert text == "<p>inner html</p>"

    def test_multipart_with_no_data_returns_none(self):
        payload = {
            "parts": [
                {"mimeType": "text/plain", "body": {}},
            ]
        }
        mime, text = get_body_from_payload(payload)
        assert mime is None
        assert text is None


# ── html_to_plain / body_to_plain ──────────────────────────────────────────────


class TestBodyToPlain:
    def test_plain_passthrough(self):
        assert body_to_plain("text/plain", "hello world") == "hello world"

    def test_none_mime_passthrough(self):
        assert body_to_plain(None, "raw text") == "raw text"

    def test_html_tags_stripped(self):
        result = body_to_plain("text/html", "<p>Hello <b>world</b></p>")
        assert "Hello" in result
        assert "world" in result
        assert "<" not in result
        assert ">" not in result

    def test_html_whitespace_normalized(self):
        result = body_to_plain("text/html", "<p>  too   many   spaces  </p>")
        assert "  " not in result

    def test_html_mime_case_insensitive(self):
        result = body_to_plain("TEXT/HTML", "<b>bold</b>")
        assert "bold" in result
        assert "<" not in result

    def test_html_to_plain_empty_string(self):
        assert html_to_plain("") == ""

    def test_html_to_plain_no_tags(self):
        assert html_to_plain("just text") == "just text"


# ── format_sent_date ───────────────────────────────────────────────────────────


class TestFormatSentDate:
    def test_internal_date_unix_ms(self):
        # 1704067200000 ms = 2024-01-01 00:00:00 UTC
        msg = {"internalDate": "1704067200000"}
        result = format_sent_date(msg)
        assert "2024-01-01" in result
        assert "UTC" in result

    def test_falls_back_to_date_header_on_bad_internal_date(self):
        msg = {
            "internalDate": "not-a-number",
            "payload": {"headers": [{"name": "Date", "value": "Mon, 1 Jan 2024 00:00:00 +0000"}]},
        }
        result = format_sent_date(msg)
        assert "Mon, 1 Jan 2024" in result

    def test_falls_back_to_date_header_when_no_internal_date(self):
        msg = {
            "payload": {"headers": [{"name": "Date", "value": "Fri, 5 Apr 2024 12:00:00 +0000"}]}
        }
        result = format_sent_date(msg)
        assert "Fri, 5 Apr 2024" in result

    def test_empty_message_returns_empty_string(self):
        assert format_sent_date({}) == ""

    def test_missing_date_header_returns_empty_string(self):
        msg = {"payload": {"headers": [{"name": "Subject", "value": "hello"}]}}
        assert format_sent_date(msg) == ""
