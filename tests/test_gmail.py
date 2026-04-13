"""Tests for gmail module: body decoding, HTML stripping, date formatting, send."""

import base64
import email as email_lib
from unittest.mock import MagicMock, patch

import pytest

from itselectric.gmail import (  # type: ignore
    body_to_plain,
    format_sent_date,
    get_body_from_payload,
    html_to_plain,
    load_template,
    send_email,
)


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


# ── load_template ──────────────────────────────────────────────────────────────


class TestLoadTemplate:
    def test_returns_subject_and_body(self, tmp_path):
        (tmp_path / "welcome.txt").write_text(
            "Welcome to It's Electric\n\nHi {name}, thanks for signing up!"
        )
        subject, body = load_template("welcome", str(tmp_path))
        assert subject == "Welcome to It's Electric"
        assert body == "Hi {name}, thanks for signing up!"

    def test_raises_on_missing_template(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent", str(tmp_path))

    def test_subject_is_first_line(self, tmp_path):
        (tmp_path / "t.txt").write_text("My Subject\n\nMy body")
        subject, _ = load_template("t", str(tmp_path))
        assert subject == "My Subject"

    def test_body_excludes_subject_line(self, tmp_path):
        (tmp_path / "t.txt").write_text("Subject\n\nLine 1\nLine 2")
        _, body = load_template("t", str(tmp_path))
        assert body == "Line 1\nLine 2"

    def test_loads_html_template(self, tmp_path):
        (tmp_path / "welcome.html").write_text(
            "Welcome!\n\n<p>Hi {name}</p>"
        )
        subject, body = load_template("welcome", str(tmp_path))
        assert subject == "Welcome!"
        assert body == "<p>Hi {name}</p>"

    def test_html_takes_priority_over_txt(self, tmp_path):
        (tmp_path / "t.html").write_text("HTML Subject\n\n<p>html body</p>")
        (tmp_path / "t.txt").write_text("TXT Subject\n\ntxt body")
        subject, body = load_template("t", str(tmp_path))
        assert subject == "HTML Subject"
        assert "<p>" in body


# ── send_email ─────────────────────────────────────────────────────────────────


class TestSendEmail:
    def _mock_service(self):
        svc = MagicMock()
        svc.users().messages().send().execute.return_value = {"id": "msg123"}
        return svc

    def test_returns_true_on_success(self):
        creds = MagicMock()
        with patch("itselectric.gmail.build", return_value=self._mock_service()):
            assert send_email(creds, "to@example.com", "Subject", "Body") is True

    def test_returns_false_on_http_error(self):
        from googleapiclient.errors import HttpError  # type: ignore
        creds = MagicMock()
        svc = MagicMock()
        svc.users().messages().send().execute.side_effect = HttpError(
            MagicMock(status=500), b"error"
        )
        with patch("itselectric.gmail.build", return_value=svc):
            assert send_email(creds, "to@example.com", "Subject", "Body") is False

    def test_sends_to_correct_address(self):
        creds = MagicMock()
        captured = {}
        svc = self._mock_service()

        original_send = svc.users().messages().send
        def capture(**kwargs):
            captured.update(kwargs)
            return original_send()
        svc.users().messages().send = capture

        with patch("itselectric.gmail.build", return_value=svc):
            send_email(creds, "driver@example.com", "Hello", "<p>Body</p>")

        raw = base64.urlsafe_b64decode(captured["body"]["raw"])
        msg = email_lib.message_from_bytes(raw)
        assert msg["to"] == "driver@example.com"

    def test_sends_html_content_type(self):
        creds = MagicMock()
        captured = {}
        svc = self._mock_service()

        original_send = svc.users().messages().send
        def capture(**kwargs):
            captured.update(kwargs)
            return original_send()
        svc.users().messages().send = capture

        with patch("itselectric.gmail.build", return_value=svc):
            send_email(creds, "x@example.com", "Subject", "<p>Hello</p>")

        raw = base64.urlsafe_b64decode(captured["body"]["raw"])
        msg = email_lib.message_from_bytes(raw)
        assert msg.get_content_type() == "text/html"

    def test_subject_in_message(self):
        creds = MagicMock()
        captured = {}
        svc = self._mock_service()

        original_send = svc.users().messages().send
        def capture(**kwargs):
            captured.update(kwargs)
            return original_send()
        svc.users().messages().send = capture

        with patch("itselectric.gmail.build", return_value=svc):
            send_email(creds, "x@example.com", "My Subject", "Body")

        raw = base64.urlsafe_b64decode(captured["body"]["raw"])
        msg = email_lib.message_from_bytes(raw)
        assert msg["subject"] == "My Subject"

    def test_html_with_images_is_multipart_related(self, tmp_path):
        img_file = tmp_path / "logo.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)  # minimal PNG-like bytes

        creds = MagicMock()
        captured = {}
        svc = self._mock_service()

        original_send = svc.users().messages().send
        def capture(**kwargs):
            captured.update(kwargs)
            return original_send()
        svc.users().messages().send = capture

        with patch("itselectric.gmail.build", return_value=svc):
            send_email(
                creds,
                "x@example.com",
                "Subject",
                '<p>Hi</p><img src="cid:logo">',
                images={"logo": str(img_file)},
            )

        raw = base64.urlsafe_b64decode(captured["body"]["raw"])
        msg = email_lib.message_from_bytes(raw)
        assert msg.get_content_type() == "multipart/related"
        payloads = msg.get_payload()
        assert any(p.get_content_type() == "text/html" for p in payloads)
        assert any(p.get("Content-ID") == "<logo>" for p in payloads)
