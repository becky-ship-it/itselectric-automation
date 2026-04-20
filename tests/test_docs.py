"""Tests for docs module: fetch email templates from Google Docs."""

from unittest.mock import MagicMock, patch

import pytest

from itselectric.docs import fetch_template_from_doc  # type: ignore


def _mock_drive_export(html: str):
    """Return a mock Drive service whose files().export().execute() returns html bytes."""
    svc = MagicMock()
    svc.files().export().execute.return_value = html.encode("utf-8")
    return svc


_SINGLE_SECTION_DOC = """\
<html><head></head><body>
<h1>tell_me_more_general</h1>
<p>Great news — EV charging near you!</p>
<p>Hi {name}, there is a charger near {address} in {city}, {state}.</p>
<p>— The It's Electric Team</p>
</body></html>
"""

_MULTI_SECTION_DOC = """\
<html><head></head><body>
<h1>tell_me_more_general</h1>
<p>General Subject</p>
<p>General body content.</p>
<h1>waitlist</h1>
<p>Waitlist Subject</p>
<p>Waitlist body content.</p>
</body></html>
"""

_LEADING_EMPTY_PARA = """\
<html><head></head><body>
<h1>my_template</h1>
<p></p>
<p>Real Subject</p>
<p>Body here.</p>
</body></html>
"""

_EMPTY_SECTION_DOC = """\
<html><head></head><body>
<h1>empty_template</h1>
</body></html>
"""


class TestFetchTemplateFromDoc:
    def test_subject_from_first_nonempty_paragraph(self):
        creds = MagicMock()
        with patch("itselectric.docs.build", return_value=_mock_drive_export(_SINGLE_SECTION_DOC)):
            subject, _ = fetch_template_from_doc(creds, "doc123", "tell_me_more_general")
        assert subject == "Great news — EV charging near you!"

    def test_body_excludes_subject_paragraph(self):
        creds = MagicMock()
        with patch("itselectric.docs.build", return_value=_mock_drive_export(_SINGLE_SECTION_DOC)):
            _, body = fetch_template_from_doc(creds, "doc123", "tell_me_more_general")
        assert "Great news" not in body

    def test_body_preserves_remaining_html(self):
        creds = MagicMock()
        with patch("itselectric.docs.build", return_value=_mock_drive_export(_SINGLE_SECTION_DOC)):
            _, body = fetch_template_from_doc(creds, "doc123", "tell_me_more_general")
        assert "{name}" in body
        assert "It's Electric Team" in body

    def test_selects_correct_section_from_multisection_doc(self):
        creds = MagicMock()
        with patch("itselectric.docs.build", return_value=_mock_drive_export(_MULTI_SECTION_DOC)):
            subject, body = fetch_template_from_doc(creds, "doc123", "waitlist")
        assert subject == "Waitlist Subject"
        assert "Waitlist body" in body
        assert "General" not in body

    def test_first_section_not_contaminated_by_second(self):
        creds = MagicMock()
        with patch("itselectric.docs.build", return_value=_mock_drive_export(_MULTI_SECTION_DOC)):
            _, body = fetch_template_from_doc(creds, "doc123", "tell_me_more_general")
        assert "Waitlist" not in body

    def test_skips_leading_empty_paragraphs_for_subject(self):
        creds = MagicMock()
        with patch("itselectric.docs.build", return_value=_mock_drive_export(_LEADING_EMPTY_PARA)):
            subject, _ = fetch_template_from_doc(creds, "doc123", "my_template")
        assert subject == "Real Subject"

    def test_raises_key_error_on_missing_template(self):
        creds = MagicMock()
        with patch("itselectric.docs.build", return_value=_mock_drive_export(_SINGLE_SECTION_DOC)):
            with pytest.raises(KeyError, match="nonexistent"):
                fetch_template_from_doc(creds, "doc123", "nonexistent")

    def test_raises_value_error_on_empty_section(self):
        creds = MagicMock()
        with patch("itselectric.docs.build", return_value=_mock_drive_export(_EMPTY_SECTION_DOC)):
            with pytest.raises(ValueError, match="no content"):
                fetch_template_from_doc(creds, "doc123", "empty_template")

    def test_uses_correct_doc_id(self):
        creds = MagicMock()
        svc = _mock_drive_export(_SINGLE_SECTION_DOC)
        with patch("itselectric.docs.build", return_value=svc):
            fetch_template_from_doc(creds, "my-doc-id-abc", "tell_me_more_general")
        svc.files().export.assert_called_with(fileId="my-doc-id-abc", mimeType="text/html")

    def test_uses_drive_v3(self):
        creds = MagicMock()
        svc = _mock_drive_export(_SINGLE_SECTION_DOC)
        with patch("itselectric.docs.build", return_value=svc) as mock_build:
            fetch_template_from_doc(creds, "doc123", "tell_me_more_general")
        mock_build.assert_called_with("drive", "v3", credentials=creds)
