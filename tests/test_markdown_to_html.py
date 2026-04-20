from src.itselectric.markdown_to_html import convert


def test_paragraph():
    assert "<p>Hello</p>" in convert("Hello")


def test_bold():
    assert "<strong>world</strong>" in convert("**world**")


def test_link():
    html = convert("[click](https://example.com)")
    assert 'href="https://example.com"' in html
    assert "click" in html


def test_empty_string():
    assert convert("") == ""


def test_multiline():
    html = convert("# Title\n\nParagraph.")
    assert "<h1>" in html
    assert "<p>Paragraph.</p>" in html
