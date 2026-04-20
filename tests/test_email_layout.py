from src.itselectric.email_layout import render_email


def test_render_email_contains_header():
    html = render_email("Hello **world**")
    assert "It's Electric" in html


def test_render_email_converts_markdown():
    html = render_email("Hello **world**")
    assert "<strong>world</strong>" in html


def test_render_email_has_body_structure():
    html = render_email("test content")
    assert "<!DOCTYPE html>" in html
    assert "test content" in html


def test_render_email_has_footer():
    html = render_email("x")
    assert "Reply to this email" in html


def test_render_empty_body():
    html = render_email("")
    assert "<!DOCTYPE html>" in html
