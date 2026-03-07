"""Regex extraction for It's Electric form emails."""

import re

# Matches the plain-text body of "it's electric" contact form emails.
# Fields: name, address, email_1, email_2.
EXTRACT_PATTERN = re.compile(
    r"\[plain\]: it's electric (?P<name>.*?) "
    r"The user has an address of (?P<address>.*?) "
    r"and has an email of\s+(?P<email_1>\S+)\s+"
    r"Email address submitted in form\s+(?P<email_2>\S+)"
)


def extract_parsed(content: str) -> dict | None:
    """
    Try to extract name, address, email_1, email_2 from plain-text email body.
    Returns a dict with those keys on match, or None if no match.
    """
    if not content:
        return None
    match = EXTRACT_PATTERN.search("[plain]: " + content)
    return match.groupdict() if match else None
