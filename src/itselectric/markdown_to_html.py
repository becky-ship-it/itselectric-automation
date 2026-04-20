"""Thin wrapper for converting Markdown text to HTML."""

import markdown as _md


def convert(body_md: str) -> str:
    """Return HTML for the given Markdown string. Returns '' for empty input."""
    if not body_md:
        return ""
    return _md.markdown(body_md, extensions=["extra"])
